import React, { useState, useRef, useEffect } from 'react';
import { useNodePilot } from '../context';

interface AnnotationUIProps {
  selectedText: string;
  position: { x: number; y: number };
  onClose: () => void;
}

export function AnnotationUI({ selectedText, position, onClose }: AnnotationUIProps) {
  const [confusionNote, setConfusionNote] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordedAudio, setRecordedAudio] = useState<Blob | null>(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioPreview, setAudioPreview] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<'text' | 'audio'>('text');
  const [audioSupported, setAudioSupported] = useState(false);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const durationTimerRef = useRef<NodeJS.Timeout | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  
  const { state, createAnnotation } = useNodePilot();

  useEffect(() => {
    // 檢查音訊設備支援
    const checkAudioSupport = async () => {
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
        setAudioSupported(true);
      } catch (error) {
        console.log('Audio not supported or no permission:', error);
        setAudioSupported(false);
      }
    };
    
    checkAudioSupport();
    
    return () => {
      // 清理計時器
      if (recordingTimerRef.current) {
        clearTimeout(recordingTimerRef.current);
      }
      if (durationTimerRef.current) {
        clearInterval(durationTimerRef.current);
      }
      // 清理音檔 URL
      if (audioPreview) {
        URL.revokeObjectURL(audioPreview);
      }
    };
  }, [audioPreview]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        }
      });
      
      audioChunksRef.current = [];
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 128000
      });
      
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // 檢查檔案大小 (12MB limit)
        if (audioBlob.size > 12 * 1024 * 1024) {
          alert('音檔檔案過大，請重新錄製（限制 12MB）');
          return;
        }
        
        setRecordedAudio(audioBlob);
        const url = URL.createObjectURL(audioBlob);
        setAudioPreview(url);
        
        // 停止所有音軌
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingDuration(0);
      
      // 開始計時
      durationTimerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
      
      // 10分鐘自動停止
      recordingTimerRef.current = setTimeout(() => {
        stopRecording();
      }, 10 * 60 * 1000);
      
    } catch (error) {
      console.error('無法存取麥克風:', error);
      alert('無法存取麥克風，請檢查權限設定');
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    
    setIsRecording(false);
    
    if (recordingTimerRef.current) {
      clearTimeout(recordingTimerRef.current);
    }
    if (durationTimerRef.current) {
      clearInterval(durationTimerRef.current);
    }
  };
  
  const resetAudio = () => {
    setRecordedAudio(null);
    if (audioPreview) {
      URL.revokeObjectURL(audioPreview);
      setAudioPreview(null);
    }
    setRecordingDuration(0);
  };
  
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSubmit = async () => {
    if (inputMode === 'text' && !confusionNote.trim()) {
      alert('請描述你的困惑或錄製音檔');
      return;
    }
    
    if (inputMode === 'audio' && !recordedAudio) {
      alert('請錄製音檔描述你的困惑');
      return;
    }

    await createAnnotation({
      url: window.location.href,
      selected_text: selectedText,
      confusion_note: confusionNote || '',
      audio_file: recordedAudio || undefined,
      page_title: document.title,
    });

    onClose();
  };

  return (
    <div
      className="nodepilot-interactive"
      style={{
        position: 'fixed',
        top: position.y + 10,
        left: position.x,
        background: 'white',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '12px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        zIndex: 10000,
        maxWidth: '300px',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        pointerEvents: 'auto',
      }}
    >
      <div style={{ marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
        選取文字: "{selectedText.substring(0, 50)}{selectedText.length > 50 ? '...' : ''}"
      </div>
      
      {/* 輸入模式切換 */}
      <div style={{ marginBottom: '8px', display: 'flex', gap: '8px' }}>
        <button
          onClick={() => setInputMode('text')}
          style={{
            background: inputMode === 'text' ? '#3b82f6' : '#f3f4f6',
            color: inputMode === 'text' ? 'white' : '#374151',
            border: 'none',
            padding: '4px 8px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '11px',
          }}
        >
          文字輸入
        </button>
        {audioSupported && (
          <button
            onClick={() => setInputMode('audio')}
            style={{
              background: inputMode === 'audio' ? '#3b82f6' : '#f3f4f6',
              color: inputMode === 'audio' ? 'white' : '#374151',
              border: 'none',
              padding: '4px 8px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '11px',
            }}
          >
            語音錄製
          </button>
        )}
        {!audioSupported && (
          <span style={{ fontSize: '10px', color: '#6b7280', alignSelf: 'center' }}>
            音訊設備不可用
          </span>
        )}
      </div>
      
      {inputMode === 'text' ? (
        <textarea
          value={confusionNote}
          onChange={(e) => setConfusionNote(e.target.value)}
          placeholder="描述你的困惑..."
          style={{
            width: '100%',
            height: '60px',
            border: '1px solid #e2e8f0',
            borderRadius: '4px',
            padding: '8px',
            resize: 'none',
            fontSize: '13px',
          }}
        />
      ) : (
        <div style={{ marginBottom: '8px' }}>
          {!recordedAudio ? (
            <div>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px',
                marginBottom: '8px'
              }}>
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={state.isLoading}
                  style={{
                    background: isRecording ? '#ef4444' : '#10b981',
                    color: 'white',
                    border: 'none',
                    padding: '8px 12px',
                    borderRadius: '50px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span style={{ 
                    width: '8px', 
                    height: '8px', 
                    backgroundColor: 'currentColor',
                    borderRadius: isRecording ? '2px' : '50%',
                    display: 'inline-block'
                  }}></span>
                  {isRecording ? '停止錄製' : '開始錄製'}
                </button>
                
                {isRecording && (
                  <span style={{ fontSize: '12px', color: '#ef4444' }}>
                    {formatDuration(recordingDuration)} / 10:00
                  </span>
                )}
              </div>
              
              {isRecording && (
                <div style={{ 
                  fontSize: '11px', 
                  color: '#6b7280',
                  textAlign: 'center'
                }}>
                  錄製中... 清楚描述你的困惑
                </div>
              )}
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: '8px', fontSize: '12px', color: '#6b7280' }}>
                錄音完成 ({formatDuration(recordingDuration)})
              </div>
              
              <audio 
                controls 
                src={audioPreview || undefined}
                style={{ width: '100%', height: '32px' }}
              />
              
              <div style={{ marginTop: '8px', display: 'flex', gap: '4px' }}>
                <button
                  onClick={resetAudio}
                  style={{
                    background: '#f3f4f6',
                    color: '#374151',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '11px',
                  }}
                >
                  重新錄製
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      
      <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
        <button
          onClick={handleSubmit}
          disabled={state.isLoading || isRecording}
          style={{
            background: (state.isLoading || isRecording) ? '#9ca3af' : '#3b82f6',
            color: 'white',
            border: 'none',
            padding: '6px 12px',
            borderRadius: '4px',
            cursor: (state.isLoading || isRecording) ? 'not-allowed' : 'pointer',
            fontSize: '12px',
          }}
        >
          {state.isLoading ? '處理中...' : isRecording ? '錄製中...' : '標註困惑'}
        </button>
        
        <button
          onClick={onClose}
          style={{
            background: '#f3f4f6',
            color: '#374151',
            border: 'none',
            padding: '6px 12px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          取消
        </button>
      </div>
      
      {state.error && (
        <div style={{ marginTop: '8px', color: '#ef4444', fontSize: '12px' }}>
          {state.error}
        </div>
      )}
    </div>
  );
}