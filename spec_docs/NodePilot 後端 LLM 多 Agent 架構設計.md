# NodePilot 後端 LLM 多 Agent 架構設計

## 系統架構總覽

**系統流程概述**：使用者在前端選取文章中的段落或名詞，並以文字或語音方式標註自己不理解的點（confusion point）。後端接收此請求後，先進行語音轉文字（如有語音輸入），再由一個小型語言模型（如 **Gemma 3N**）理解使用者的困惑語意，將其視為「知識缺口」（Gap Context），並結合文章內容（Article Context）產生待辦任務清單（Todo List）。接著，系統的調度器會按照清單將各項任務委派給不同專門的 **Agent** 處理，包括：網路查詢、筆記庫檢索、向大型模型請求教學說明等。各 Agent 完成子任務後，結果將整合為最終回應，以 HTML/Chat UI 格式呈現給使用者，並支援後續多輪追問。使用者也可選擇將最終結果轉存為 Markdown 筆記到 Obsidian。下圖展示了這種「先規劃、再執行」的多代理架構流程[^1]。

*計畫-執行 (Plan-and-Execute) 型多 Agent 架構示意圖。左側大型模型先產生完整計畫（Todo 任務清單），右側多個執行者依序或並行完成各子任務，最後彙總答案回覆使用者。此設計避免大型模型重覆參與每一步驟，降低成本並提高執行效率*[^1]。

上述架構充分利用**大型語言模型作為中樞**進行任務分解與決策，同時結合多個**專家 Agent**執行不同類型的任務，屬於經典的「Plan and Execute」多代理模式[^2][^3]。在此模式下，大型模型或中型模型擔任**策劃者（Planner）**，先對整體問題進行推理，產生完整的解題步驟；然後由各種**執行者（Executors）**按照步驟要求，使用特定工具或模型完成任務，最後將結果交由策劃者或調度模組匯總成最終答案[^4][^5]。這種架構相較於傳統單一 Agent 的 ReAct 循環，具有**更高的效率與穩定性**：一方面，大型模型不需參與每個子步驟，大幅減少不必要的 API 呼叫次數和成本[^1]；另一方面，透過讓模型**顯式規劃 Chain-of-Thought**，強迫其一次考慮全局步驟，可提升任務完成的整體正確率和質量[^6]。Anthropic 的研究也證實，讓一個主代理分解任務給多個子代理並行執行，能較單一代理更快速且全面地找到答案[^7]。因此，NodePilot 後端採用此多 Agent 協作架構，有助於在**保證回答品質**的同時提升處理速度和可靠性。

## Agent 角色與模型配置

每個 Agent 在系統中擔任不同職責，對應選用最適合的模型或工具。下表列出了主要 Agent 的功能、使用的模型技術，以及預計的備援機制：

| Agent/模組 | 職責 | 使用模型/工具 | 備援方案 |
| :--- | :--- | :--- | :--- |
| **語音轉文字 Agent** | 將使用者的語音困惑描述轉成文字 | OpenAI Whisper API（雲端）[^8] | 本地 Whisper 模型 (如 large-v2)[^9]；或 Voxtral mini 3B 模型[^10] |
| **任務規劃 Agent** | 語意理解用戶困惑，生成任務 Todo 清單 | 小型 LLM：「Gemma 3N」 (本地 3B級模型) | 若小模型無法勝任，視情況可切換 GPT-3.5 等雲端模型 |
| **網路搜尋 Agent** | 執行網路資訊查詢（需取得用戶許可） | 網路搜尋 API（如 Bing Search 或 Google API） | 若使用者未授權或搜尋無果，則跳過或嘗試其他途徑 |
| **筆記檢索 Agent** | 在使用者 Obsidian 筆記庫中檢索相關內容 | 向量資料庫 + 相似度查詢 (Retrieval)[^11] | 若無筆記命中，則跳過此任務 |
| **教學內容生成 Agent** | 統合資訊，產生講解/範例/圖解等內容 | 大型 LLM（API）：如 Anthropic Claude 3.5 or 4、OpenAI GPT-4o/GPT-5，或 Google Gemini | 備用模型：其他可用 API（如 GPT-4 vs Claude 互為後備）或本地大型模型（如 Llama2-70B） |
| **圖表繪製 Agent** (可選) | 產生示意圖或流程圖（Mermaid、Kv-Cache 圖解等） | LLM 工具使用：提示大模型輸出 Mermaid 語法圖，或結合 Graphviz/DALL-E 等繪圖工具 | 若大模型無法產生有效圖表，則以文字說明代替 |
| **結果整合/格式化模組** | 將各 Agent 結果打包成最終回應內容 | 自訂 Python 邏輯組裝 HTML/Markdown，或輔以 LLM微調格式 | 若部分子任務失敗，略過該部分並標記通知用戶 |

以上各 Agent 多數以 **API** 形式調用雲端模型服務，但亦考慮了**本地模型**作為替補[^8]。例如語音轉文字優先使用 OpenAI Whisper 雲端服務獲取高準確度轉錄；但因 Whisper 屬開源模型，也可離線部署以滿足隱私需求或避免網路不穩[^10]。同樣地，大型生成模型方面，可預設以 Claude 2 或 GPT-4 等高性能模型產生教學內容，但也要實現接口的靈活切換。

值得注意的是，小型任務規劃模型 **Gemma 3N** 在本架構中扮演**任務大腦**的角色。它負責理解使用者的提問語境並**拆解複雜任務**，因此要求對語意有良好理解力，同時推理成本低廉。採用本地 3B 等級模型可大幅降低延遲和 API 成本，並保障資料隱私。如果發現 Gemma 3N 對某些複雜語句理解不佳，我們可以在框架中設計 **fallback 邏輯**：例如當規劃結果明顯不合理時，自動改用更強的模型（如 GPT-3.5）來重新生成任務清單，以提高可靠性。

## 任務處理流程與 Context 級聯整合

1.  **使用者標註輸入**：使用者在前端選中文章中的重點文字或段落（作為**文章 Context** 輸入），並提交自己的疑問/困惑描述。如果使用語音輸入，系統會**立即觸發 Whisper API** 將音訊轉為文字[^12]。
2.  **語意理解與任務拆解**：後端將文章片段和用戶困惑（Gap Context）提交給**任務規劃 Agent**（Gemma 3N 小模型）。為提升小模型理解力，我們會提供盡可能完整且精簡的上下文：首先對長文章做**分段向量化**處理，尋找與用戶選取內容最相關的若干段落[^11]；再將這些相關段與用戶困惑描述一起作為提示，輸入給小模型。小模型輸出結果為一份**待辦任務清單（Todo List）**。
3.  **任務委派與執行**：系統內建的**調度器**會解析小模型產生的 Todo 清單，並逐條讀取任務，交由相應的 Agent 處理。
    *   *資料查詢任務* – 觸發**網路搜尋 Agent**。
    *   *知識庫檢索任務* – 觸發**筆記檢索 Agent**，對 Obsidian 筆記向量資料庫進行相似度比對[^11]。這是一種典型的檢索增強生成（RAG）流程[^13]。
    *   *教學生成任務* – 觸發**大型模型 Agent**。
    *   *繪圖任務* – 由大型模型 Agent 直接產生圖表描述（例如 Mermaid 語法），或引入專門的**圖表繪製 Agent**。
    調度器在執行任務時，可**同步或異步**處理各 Agent[^14][^15]。在 Anthropic 的多 Agent 研究系統中，他們透過**主代理 + 並行子代理**模式，大幅拓寬了搜尋範圍，提高了整體解題效率[^7][^14]。
4.  **結果整合與回覆生成**：所有子任務完成後，調度器將收集到的資訊與內容交給**結果整合模組**，組裝為結構化的回答。
5.  **多輪追問與筆記存儲**：生成的教學內容會透過前端介面回傳給使用者。系統會**保留對話上下文**，支援後續追問。使用者滿意後，可將最終教學內容轉換為純 Markdown 格式，存入 Obsidian 筆記庫。

## 模型切換與 Fallback 策略

為保障系統穩定性，我們設計了以下策略：

*   **Whisper 語音 API 失效或延遲**：如遇 API 響應過慢或超時[^12]，系統將自動切換至本地的 Whisper 模型執行轉錄[^8][^9]。
*   **小模型規劃品質不佳**：若 Gemma 3N 出現明顯錯漏，系統將啟用**模型升級 fallback**，改用更強的模型（例如 GPT-4）重做任務拆解[^6]。
*   **大型模型 API 限制與切換**：如果主 API（如 OpenAI GPT-4）達到速率限制，調度器將自動改調用另一套 API，例如 Anthropic Claude 2 或本地部署的 Llama2 70B 模型。
*   **工具/Agent 失敗處理**：如果某個子任務的 Agent 執行失敗，調度器會根據任務重要性採取不同措施，如重試、跳過或請求重新規劃[^16]。
*   **多 Agent 協作一致性**：在結果整合階段進行**一致性檢查**，避免不同 Agent 返回的資訊相互矛盾。在 Anthropic 多 Agent 系統的經驗中，給子代理明確且互補的任務定義非常重要[^17]。

綜上，本架構通過**多層次的 fallback** 確保穩定：從模型選擇上，同一任務配置多套模型備援[^18]；從流程邏輯上，每步驟失敗都有預案處理。

## 多 Agent 調度框架的選擇

在實現上述多 Agent 架構時，可以考慮採用現有的 LLM 代理框架，或自行開發。

*   **LangChain + LangGraph**：LangGraph 是專門用於**Agent 流程編排**的擴充套件[^19]。我們可以將 Agent 流程定義為一個**有向圖**，由框架自動調度執行[^20][^21][^22][^23]。然而，LangChain 的靈活性也增加了系統複雜度[^24]。
*   **Microsoft AutoGen**：AutoGen 強調讓多個 Agent 通過類聊天的方式交互協作[^25]，較適合需要 Agent 間反覆討論的複雜研究任務[^26]。
*   **CrewAI**：這是一個專為**多代理協作**設計的框架[^27]，強調跨 Agent 的**任務分工**和**自治性**[^28]，且內建對多 LLM 供應商的整合[^29]。
*   **自行實作 Python 調度**：基於 FastAPI 後端，手工實現調度邏輯。優點是**可控性強**、調試方便，不受制於框架限制[^30]。

綜合考量，我們建議優先**自行開發輕量的調度模組**，配合部分現有工具庫使用，以確保**先驗證核心功能**，再引入框架疊代，降低開發風險[^24]。

## Chain of Thought 穩定性與回饋追蹤機制

為加強系統的 **Chain of Thought (CoT)** 處理，我們採取以下措施：

*   **顯式任務鏈劃分**：透過讓小模型生成完整的任務清單，將推理步驟明確化，提升了推理的穩定性和可控性[^1][^6][^31]。
*   **上下文級聯傳遞**：利用檢索增強生成（RAG）的應用，將外部文件（如筆記或網搜結果）作為輔助 context 拼入提示，減少幻覺風險[^32]。
*   **中間結果記錄與變數引用**：將子任務的結果存入暫存區並賦予標識符，方便後續任務引用[^23][^33]，也為 Agent 的**自我反思（Self-Reflection）** 提供素材[^34]。
*   **使用者反饋迴圈**：引入使用者的反饋作為調整依據，形成**人機協同**的 CoT 改進機制[^16]。
*   **提示工程與多 Agent Prompt 規範**：為每種 Agent 制定專門的 Prompt 模板，確保模型理解自身角色和輸出格式。精心設計的提示對避免代理失誤至關重要[^16][^35]。
*   **評估與監控**：引入自動化評估機制，並保存全鏈路日誌，方便排查錯誤。可借鑑 Reflexion 方法[^34]，讓模型事後讀取日誌，尋找改進空間。

總而言之，本架構透過明確的任務鏈劃分和嚴謹的調度機制，將大型模型的 Chain of Thought 顯性化、結構化，最終達到一個**高穩定、高可解釋**的多 Agent LLM 系統[^1][^32]。

---

[^1]: https://blog.langchain.com/planning-agents/
[^2]: https://ingliguori.medium.com/hugginggpt-a-new-way-to-solve-complex-ai-tasks-with-language-602b6f5b263c
[^3]: https://ingliguori.medium.com/hugginggpt-a-new-way-to-solve-complex-ai-tasks-with-language-602b6f5b263c
[^4]: https://ingliguori.medium.com/hugginggpt-a-new-way-to-solve-complex-ai-tasks-with-language-602b6f5b263c
[^5]: https://www.infoq.com/news/2023/04/hugginggpt-complex-ai-tasks/
[^6]: https://blog.langchain.com/planning-agents/
[^7]: https://www.anthropic.com/engineering/multi-agent-research-system
[^8]: https://webflow.assemblyai.com/blog/openai-whisper-developers-choosing-api-local-server-side-transcription
[^9]: https://webflow.assemblyai.com/blog/openai-whisper-developers-choosing-api-local-server-side-transcription
[^10]: file://file-PFmzsy8suWjNh52R77AozK
[^11]: https://publish.obsidian.md/mrd-brain/Knowledge+Base/Artificial+Intelligence/Retrieval+Augmented+Generation
[^12]: file://file-PFmzsy8suWjNh52R77AozK
[^13]: https://publish.obsidian.md/mrd-brain/Knowledge+Base/Artificial+Intelligence/Retrieval+Augmented+Generation
[^14]: https://www.anthropic.com/engineering/multi-agent-research-system
[^15]: https://www.anthropic.com/engineering/multi-agent-research-system
[^16]: https://www.anthropic.com/engineering/multi-agent-research-system
[^17]: https://www.anthropic.com/engineering/multi-agent-research-system
[^18]: https://hackmd.io/@YungHuiHsu/rkK52BkQp
[^19]: https://www.langchain.com/langgraph
[^20]: https://blog.langchain.com/planning-agents/
[^21]: https://blog.langchain.com/planning-agents/
[^22]: https://blog.langchain.com/planning-agents/
[^23]: https://blog.langchain.com/planning-agents/
[^24]: https://hackmd.io/@YungHuiHsu/rkK52BkQp
[^25]: https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat/
[^26]: https://www.anthropic.com/engineering/multi-agent-research-system
[^27]: https://medium.com/pythoneers/building-a-multi-agent-system-using-crewai-a7305450253e
[^28]: https://docs.crewai.com/
[^29]: https://docs.crewai.com/concepts/llms
[^30]: https://hackmd.io/@YungHuiHsu/rkK52BkQp
[^31]: https://blog.langchain.com/planning-agents/
[^32]: https://www.anthropic.com/engineering/multi-agent-research-system
[^33]: https://blog.langchain.com/planning-agents/
[^34]: https://hackmd.io/@YungHuiHsu/rkK52BkQp
[^35]: https://www.anthropic.com/engineering/multi-agent-research-system