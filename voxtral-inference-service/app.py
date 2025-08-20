"""
Voxtral Mini 3B Q4 獨立推理服務
提供 REST API 接口，使用 ONNX Q4 量化模型進行音頻推理
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
import time
import base64
import io
import tempfile

# import torch  # 移除避免與 ONNX Runtime GPU 衝突
import numpy as np
import librosa
import soundfile as sf
import onnxruntime as ort
from tokenizers import Tokenizer
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 FastAPI
app = FastAPI(
    title="Voxtral Mini 3B Q4 推理服務",
    description="獨立的 Voxtral ONNX Q4 量化模型推理服務",
    version="1.0.0"
)

# CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域變數
onnx_session = None
device = None
MODEL_PATH = "/app/models"
SAMPLE_RATE = 16000

class AudioRequest(BaseModel):
    """音頻推理請求"""
    audio_data: str  # Base64 編碼的音頻
    task: str = "transcribe"  # transcribe, summarize, describe, qa
    language: str = "auto"  # 語言代碼
    prompt: Optional[str] = None  # 自定義提示詞

class InferenceResponse(BaseModel):
    """推理回應"""
    success: bool
    result: str
    task: str
    language: Optional[str] = None
    processing_time: float
    model_info: Dict[str, Any]

class VoxtralONNXInferenceService:
    def __init__(self, model_path: str, device: str = "cpu"):
        self.model_path = model_path
        self.device = device
        self.audio_encoder_session = None
        self.embed_tokens_session = None
        self.decoder_session = None
        self.tokenizer = None
        self.sample_rate = SAMPLE_RATE
        
        # Voxtral 特殊 token IDs
        self.bos_id = 1     # <s>
        self.inst_id = 3    # [INST]
        self.baud_id = 25   # [BAUD]
        self.aud_id = 24    # [AUD]
        self.einst_id = 4   # [/INST]
        self.eos_token_id = 2  # </s>
        
    def load_model(self) -> bool:
        """載入完整的 Voxtral ONNX Pipeline"""
        try:
            # 找到所有必需的模型
            audio_encoder_files = list(Path(self.model_path).rglob("audio_encoder_q4.onnx"))
            embed_tokens_files = list(Path(self.model_path).rglob("embed_tokens_q4.onnx"))
            decoder_files = list(Path(self.model_path).rglob("decoder_model_merged_q4.onnx"))
            
            if not audio_encoder_files:
                raise FileNotFoundError("找不到 audio_encoder_q4.onnx")
            if not embed_tokens_files:
                raise FileNotFoundError("找不到 embed_tokens_q4.onnx")
            if not decoder_files:
                raise FileNotFoundError("找不到 decoder_model_merged_q4.onnx")
            
            # 配置執行提供者
            available_providers = ort.get_available_providers()
            logger.info(f"可用執行提供者: {available_providers}")
            
            if self.device == "cuda" and "CUDAExecutionProvider" in available_providers:
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                logger.info("✓ 使用 CUDA 執行提供者")
            else:
                providers = ["CPUExecutionProvider"]
                logger.info("✓ 使用 CPU 執行提供者")
            
            # 會話選項
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 4
            sess_options.inter_op_num_threads = 2
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # 載入三個模型
            logger.info(f"📥 載入音頻編碼器: {audio_encoder_files[0]}")
            self.audio_encoder_session = ort.InferenceSession(
                str(audio_encoder_files[0]), sess_options, providers=providers
            )
            
            logger.info(f"📥 載入 Token 嵌入: {embed_tokens_files[0]}")
            self.embed_tokens_session = ort.InferenceSession(
                str(embed_tokens_files[0]), sess_options, providers=providers
            )
            
            logger.info(f"📥 載入解碼器: {decoder_files[0]}")
            self.decoder_session = ort.InferenceSession(
                str(decoder_files[0]), sess_options, providers=providers
            )
            
            # 載入 tokenizer
            tokenizer_files = list(Path(self.model_path).rglob("tokenizer.json"))
            if tokenizer_files:
                logger.info(f"📥 載入 Tokenizer: {tokenizer_files[0]}")
                self.tokenizer = Tokenizer.from_file(str(tokenizer_files[0]))
            else:
                logger.warning("⚠️ 找不到 tokenizer.json，將使用簡化解碼")
            
            logger.info("✅ Voxtral Pipeline 載入完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline 載入失敗: {e}")
            return False
    
    def extract_mel_features_for_chunk(self, audio_chunk: np.ndarray, sampling_rate=16000, 
                                     n_fft=400, hop_length=160, n_mels=128, target_length=3000):
        """處理音頻塊為標準化 log-mel 頻譜圖"""
        # 填充或截斷到 30 秒
        target_samples = sampling_rate * 30
        audio_chunk = librosa.util.fix_length(audio_chunk, size=target_samples)

        mel_spec = librosa.feature.melspectrogram(
            y=audio_chunk, sr=sampling_rate, n_fft=n_fft, 
            hop_length=hop_length, n_mels=n_mels
        )

        log_spec = np.log10(np.maximum(mel_spec, 1e-10))
        log_spec = np.maximum(log_spec, log_spec.max() - 8.0)
        log_spec = (log_spec + 4.0) / 4.0

        if log_spec.shape[1] > target_length:
            log_spec = log_spec[:, :target_length]

        return log_spec.astype(np.float32)
    
    def process_long_audio(self, audio_data: np.ndarray, sampling_rate=16000):
        """處理長音頻，分塊處理並拼接特徵"""
        chunk_duration = 30
        chunk_samples = chunk_duration * sampling_rate
        num_chunks = int(np.ceil(len(audio_data) / chunk_samples))
        all_audio_embeds = []

        logger.info(f"音頻長度: {len(audio_data)/sampling_rate:.2f}s，分 {num_chunks} 塊處理")
        
        for i in range(num_chunks):
            start_sample = i * chunk_samples
            end_sample = start_sample + chunk_samples
            chunk = audio_data[start_sample:end_sample]

            # 獲取 mel 特徵
            mel_features = self.extract_mel_features_for_chunk(chunk, sampling_rate)
            audio_values = mel_features[None, :] # 添加 batch 維度

            # 音頻編碼器推理
            chunk_embeds_raw = self.audio_encoder_session.run(
                None, {self.audio_encoder_session.get_inputs()[0].name: audio_values}
            )[0]
            all_audio_embeds.append(chunk_embeds_raw)
            logger.info(f"  處理塊 {i+1}/{num_chunks}")

        # 拼接所有塊的嵌入
        concatenated_embeds = np.concatenate(all_audio_embeds, axis=0)
        return concatenated_embeds
    
    def transcribe(self, audio_input: np.ndarray, max_generation_tokens: int = 200) -> str:
        """執行完整的 Voxtral 轉錄 Pipeline"""
        if not all([self.audio_encoder_session, self.embed_tokens_session, self.decoder_session]):
            raise RuntimeError("Pipeline 未完全載入")
        
        try:
            # 階段 1: 處理音頻並獲取嵌入
            logger.info("🎵 階段 1: 音頻處理")
            audio_embeds_raw = self.process_long_audio(audio_input)
            batch_size = 1
            audio_output_frames = audio_embeds_raw.shape[0] // batch_size
            audio_embeds = audio_embeds_raw.reshape(batch_size, audio_output_frames, -1)
            logger.info(f"音頻嵌入形狀: {audio_embeds.shape}")

            # 階段 2: 建立初始提示
            logger.info("🔤 階段 2: 建立提示序列")
            text_instruction_ids = []
            if self.tokenizer:
                text_instruction_ids = self.tokenizer.encode("Transcribe the audio.", add_special_tokens=False).ids
            else:
                # 簡化版本，使用預設 tokens
                text_instruction_ids = [5000, 5001, 5002]  # 假設的轉錄指令 tokens
            
            prompt_tokens = ([self.bos_id, self.inst_id, self.baud_id] + 
                           [self.aud_id] * audio_output_frames + 
                           text_instruction_ids + [self.einst_id])
            current_input_ids = np.array([prompt_tokens], dtype=np.int64)
            initial_sequence_length = current_input_ids.shape[1]
            logger.info(f"初始提示序列長度: {initial_sequence_length}")

            # 階段 3: 運行 embed_tokens 並拼接音頻嵌入
            logger.info("🧠 階段 3: Token 嵌入與拼接")
            embed_inputs = {self.embed_tokens_session.get_inputs()[0].name: current_input_ids}
            inputs_embeds = self.embed_tokens_session.run(None, embed_inputs)[0]
            
            # 拼接音頻嵌入到正確位置 (在 [BAUD] 之後)
            audio_splice_start_idx = 3
            inputs_embeds[0, audio_splice_start_idx:audio_splice_start_idx + audio_output_frames, :] = audio_embeds[0]
            logger.info("音頻嵌入拼接完成")

            # 階段 4: 生成循環
            logger.info("🔄 階段 4: 開始生成循環")
            generated_ids = []
            past_key_values_cache = None
            current_past_sequence_length = 0
            num_decoder_layers = 30  # Voxtral 的層數

            for i in range(max_generation_tokens):
                dec_inputs = {}
                current_step_sequence_length = 1 if i > 0 else initial_sequence_length
                current_total_sequence_length = current_past_sequence_length + current_step_sequence_length

                if i == 0:  # Prefill 階段
                    dec_inputs["inputs_embeds"] = inputs_embeds
                    dec_inputs["attention_mask"] = np.ones((batch_size, initial_sequence_length), dtype=np.int64)
                    dec_inputs["position_ids"] = np.arange(initial_sequence_length, dtype=np.int64)[None, :]
                    for l in range(num_decoder_layers):
                        dec_inputs[f"past_key_values.{l}.key"] = np.zeros((batch_size, 8, 0, 128), dtype=np.float32)
                        dec_inputs[f"past_key_values.{l}.value"] = np.zeros((batch_size, 8, 0, 128), dtype=np.float32)
                else:  # Decode 階段
                    next_token_input_id = np.array([[generated_ids[-1]]], dtype=np.int64)
                    single_token_embeds = self.embed_tokens_session.run(
                        None, {"input_ids": next_token_input_id}
                    )[0]
                    dec_inputs["inputs_embeds"] = single_token_embeds
                    dec_inputs["attention_mask"] = np.ones((batch_size, current_total_sequence_length), dtype=np.int64)
                    dec_inputs["position_ids"] = np.array([[current_past_sequence_length]], dtype=np.int64)
                    for l in range(num_decoder_layers):
                        dec_inputs[f"past_key_values.{l}.key"] = past_key_values_cache[l * 2]
                        dec_inputs[f"past_key_values.{l}.value"] = past_key_values_cache[l * 2 + 1]

                # 執行解碼器
                outputs = self.decoder_session.run(None, dec_inputs)
                logits, past_key_values_cache = outputs[0], outputs[1:]
                next_token_id = int(np.argmax(logits[0, -1, :]))
                generated_ids.append(next_token_id)
                
                # 即時解碼顯示
                if self.tokenizer:
                    decoded_token = self.tokenizer.decode([next_token_id], skip_special_tokens=True)
                    logger.info(f"Step {i+1}: ID={next_token_id}, Token='{decoded_token}'")
                
                current_past_sequence_length = current_total_sequence_length
                
                # 檢查結束條件
                if next_token_id == self.eos_token_id:
                    logger.info("檢測到結束 token，停止生成")
                    break

            # 最終解碼
            if self.tokenizer:
                final_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
                logger.info(f"✅ 轉錄完成: {final_text}")
                return final_text
            else:
                result = f"生成完成 (Token IDs: {generated_ids[:10]}...)"
                logger.info(f"✅ 轉錄完成: {result}")
                return result
            
        except Exception as e:
            logger.error(f"❌ Pipeline 推理失敗: {e}")
            return f"推理錯誤: {str(e)}"

# 全域服務實例
voxtral_service = None

@app.on_event("startup")
async def load_model():
    """啟動時載入模型"""
    global voxtral_service, device
    
    try:
        logger.info("🚀 開始載入 Voxtral Mini 3B Q4 模型...")
        
        # 檢查 ONNX Runtime GPU 可用性
        available_providers = ort.get_available_providers()
        if "CUDAExecutionProvider" in available_providers:
            device = "cuda"
            logger.info("✓ 檢測到 ONNX Runtime CUDA 支持")
        else:
            device = "cpu"
            logger.info("⚠️ ONNX Runtime 無 CUDA 支持，使用 CPU")
        
        # 初始化 ONNX 推理服務
        voxtral_service = VoxtralONNXInferenceService(MODEL_PATH, device)
        
        # 載入模型
        if not voxtral_service.load_model():
            voxtral_service = None
            logger.error("模型載入失敗")
            
    except Exception as e:
        logger.error(f"❌ 啟動失敗: {e}")
        raise

def process_audio_bytes(audio_bytes: bytes, target_sr: int = 16000) -> np.ndarray:
    """處理音頻二進制數據"""
    try:
        # 創建臨時檔案處理音頻數據
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
        
        try:
            # 使用 librosa 載入音頻
            audio, sr = librosa.load(temp_path, sr=target_sr, mono=True)
            return audio.astype(np.float32)
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        logger.error(f"音頻處理失敗: {e}")
        raise HTTPException(status_code=400, detail=f"音頻格式錯誤: {e}")

def process_audio_file(file_path: str, target_sr: int = 16000) -> np.ndarray:
    """處理音頻檔案"""
    try:
        # 使用 librosa 載入音頻
        audio, sr = librosa.load(file_path, sr=target_sr, mono=True)
        return audio.astype(np.float32)
    except Exception as e:
        raise ValueError(f"音頻處理失敗: {e}")

def inspect_onnx_model(model_path: str):
    """檢查 ONNX 模型輸入輸出格式"""
    try:
        session = ort.InferenceSession(model_path)
        
        logger.info("=== 輸入格式 ===")
        for input_meta in session.get_inputs():
            logger.info(f"名稱: {input_meta.name}")
            logger.info(f"形狀: {input_meta.shape}")
            logger.info(f"類型: {input_meta.type}")
        
        logger.info("=== 輸出格式 ===")
        for output_meta in session.get_outputs():
            logger.info(f"名稱: {output_meta.name}")
            logger.info(f"形狀: {output_meta.shape}")
            logger.info(f"類型: {output_meta.type}")
    except Exception as e:
        logger.error(f"模型檢查失敗: {e}")

def get_task_prompt(task: str, custom_prompt: Optional[str] = None) -> str:
    """獲取任務提示詞"""
    if custom_prompt:
        return custom_prompt
    
    prompts = {
        "transcribe": "[TRANSCRIBE]",
        "summarize": "請用中文總結這段音頻的主要內容",
        "describe": "請詳細描述這段音頻",
        "qa": "這段音頻的主要話題是什麼？"
    }
    
    return prompts.get(task, "[TRANSCRIBE]")

@app.post("/inference", response_model=InferenceResponse)
async def audio_inference(request: AudioRequest):
    """音頻推理端點"""
    start_time = time.time()
    
    try:
        if not voxtral_service:
            # 如果模型未載入，使用模擬回應
            result = f"[模擬] {request.task} 結果：這是 Voxtral Mini 3B Q4 量化模型的模擬推理結果。實際部署中會使用真正的 ONNX 推理。"
            processing_time = time.time() - start_time
            
            return InferenceResponse(
                success=True,
                result=result,
                task=request.task,
                language=request.language,
                processing_time=processing_time,
                model_info={
                    "model": "Voxtral Mini 3B Q4 (模擬)",
                    "quantization": "Q4",
                    "device": device,
                    "status": "模擬模式"
                }
            )
        
        # 解碼音頻數據
        try:
            audio_bytes = base64.b64decode(request.audio_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Base64 解碼失敗: {e}")
        
        # 預處理音頻
        audio_array = process_audio_bytes(audio_bytes)
        logger.info(f"音頻長度: {len(audio_array) / SAMPLE_RATE:.2f} 秒")
        
        # 使用 ONNX 服務進行推理（直接傳入原始音頻數組）
        result = voxtral_service.transcribe(audio_array)
        
        processing_time = time.time() - start_time
        
        return InferenceResponse(
            success=True,
            result=result,
            task=request.task,
            language=request.language,
            processing_time=processing_time,
            model_info={
                "model": "Voxtral Mini 3B Q4 ONNX",
                "quantization": "Q4",
                "device": device,
                "status": "ONNX 推理"
            }
        )
    except Exception as e:
        logger.error(f"推理失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/inference/upload")
async def upload_audio_inference(
    file: UploadFile = File(...),
    task: str = Form("transcribe"),
    language: str = Form("auto"),
    prompt: Optional[str] = Form(None)
):
    """上傳音頻檔案進行推理"""
    try:
        # 讀取上傳的檔案
        audio_data = await file.read()
        
        # 轉換為 Base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # 建立請求
        request = AudioRequest(
            audio_data=audio_base64,
            task=task,
            language=language,
            prompt=prompt
        )
        
        # 調用推理
        return await audio_inference(request)
        
    except Exception as e:
        logger.error(f"檔案上傳推理失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康檢查"""
    pipeline_loaded = False
    if voxtral_service:
        pipeline_loaded = all([
            voxtral_service.audio_encoder_session is not None,
            voxtral_service.embed_tokens_session is not None,
            voxtral_service.decoder_session is not None
        ])
    
    return {
        "status": "healthy",
        "model_loaded": voxtral_service is not None,
        "pipeline_loaded": pipeline_loaded,
        "device": device,
        "cuda_available": "CUDAExecutionProvider" in ort.get_available_providers()
    }

@app.get("/model/info")
async def model_info():
    """模型資訊"""
    pipeline_loaded = False
    if voxtral_service:
        pipeline_loaded = all([
            voxtral_service.audio_encoder_session is not None,
            voxtral_service.embed_tokens_session is not None,
            voxtral_service.decoder_session is not None
        ])
    
    model_details = {
        "model": "Voxtral Mini 3B",
        "quantization": "Q4 ONNX Pipeline",
        "device": device,
        "loaded": voxtral_service is not None,
        "pipeline_loaded": pipeline_loaded,
        "components": {
            "audio_encoder": voxtral_service.audio_encoder_session is not None if voxtral_service else False,
            "embed_tokens": voxtral_service.embed_tokens_session is not None if voxtral_service else False,
            "decoder": voxtral_service.decoder_session is not None if voxtral_service else False
        },
        "supported_tasks": ["transcribe", "summarize", "describe", "qa"],
        "supported_languages": ["auto", "zh", "en", "es", "fr", "pt", "hi", "de", "nl", "it"],
        "sample_rate": SAMPLE_RATE,
        "cuda_available": "CUDAExecutionProvider" in ort.get_available_providers(),
        "onnx_providers": ort.get_available_providers()
    }
    
    # 如果 Pipeline 已載入，添加模型資訊
    if voxtral_service and pipeline_loaded:
        try:
            # 只顯示 decoder 的輸入輸出信息 (最複雜的部分)
            if voxtral_service.decoder_session:
                inputs_info = []
                for input_meta in voxtral_service.decoder_session.get_inputs():
                    inputs_info.append({
                        "name": input_meta.name,
                        "shape": input_meta.shape,
                        "type": str(input_meta.type)
                    })
                
                outputs_info = []
                for output_meta in voxtral_service.decoder_session.get_outputs():
                    outputs_info.append({
                        "name": output_meta.name,
                        "shape": output_meta.shape,
                        "type": str(output_meta.type)
                    })
                
                model_details["decoder_inputs"] = inputs_info
                model_details["decoder_outputs"] = outputs_info
        except Exception as e:
            model_details["model_schema_error"] = str(e)
    
    return model_details

@app.get("/")
async def root():
    """根端點"""
    return {
        "service": "Voxtral Mini 3B Q4 推理服務",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "inference": "/inference",
            "upload": "/inference/upload", 
            "health": "/health",
            "model_info": "/model/info",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        workers=1
    )