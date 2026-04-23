"use client";

import { useEffect, useState, Suspense, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, NewsArticle, SECFiling, StockResearch, RedditPost, CongressTrade } from "@/lib/api";
import ReactMarkdown from 'react-markdown';
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

// ── Types ─────────────────────────────────────────────────────────────────────

type Tab = "overview" | "articles" | "filings" | "financials" | "social" | "politics";

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function formatLargeNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return "-";
  const absNum = Math.abs(num);
  if (absNum >= 1e12) return `${num < 0 ? '-' : ''}$${(absNum / 1e12).toFixed(2)}T`;
  if (absNum >= 1e9) return `${num < 0 ? '-' : ''}$${(absNum / 1e9).toFixed(2)}B`;
  if (absNum >= 1e6) return `${num < 0 ? '-' : ''}$${(absNum / 1e6).toFixed(2)}M`;
  return `${num < 0 ? '-' : ''}$${absNum.toLocaleString()}`;
}

function formatPercent(num: number | null | undefined): string {
  if (num === null || num === undefined) return "-";
  return `${(num * 100).toFixed(2)}%`;
}

function formatTimestamp(utc: number): string {
  if (!utc) return "";
  const d = new Date(utc * 1000);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const POPULAR = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META", "GOOG"];

// ── Small UI Components ───────────────────────────────────────────────────────

function TabButton({ active, label, count, onClick }: { active: boolean; label: string; count?: number; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`px-4 py-2.5 text-sm font-semibold transition-all border-b-2 whitespace-nowrap ${active ? "border-sto-accent text-sto-accent" : "border-transparent text-sto-muted hover:text-sto-text"}`}>
      {label}{count !== undefined ? ` (${count})` : ""}
    </button>
  );
}

function FilingRow({ filing, onDeepDive }: { filing: SECFiling; onDeepDive: (url: string) => void }) {
  return (
    <div className="p-5 hover:bg-sto-bg transition group">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-xs font-mono font-bold text-sto-accent bg-sto-accent/10 px-2 py-0.5 rounded">{filing.form}</span>
            <span className="text-sto-muted text-xs">Filed {filing.filing_date}</span>
            {filing.period && (
              <>
                <span className="text-sto-muted text-xs">·</span>
                <span className="text-xs text-sto-muted">Period: {filing.period}</span>
              </>
            )}
          </div>
          <p className="text-sm font-medium text-sto-text group-hover:text-sto-accent line-clamp-2 leading-snug">{filing.description}</p>
          <p className="text-xs text-sto-muted mt-1">{filing.company}</p>
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          <a href={filing.url} target="_blank" rel="noopener noreferrer" className="text-xs text-sto-accent hover:underline font-medium">View on EDGAR →</a>
          <button 
            onClick={() => onDeepDive(filing.url)}
            className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded hover:bg-emerald-500/20 transition flex items-center gap-2"
          >
            <span>🧠</span> Deep Dive
          </button>
        </div>
      </div>
    </div>
  );
}

function ScoreItem({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="flex flex-col gap-1 border-l-2 border-emerald-500/20 pl-4 py-1">
      <p className="text-[10px] font-bold text-sto-muted uppercase tracking-widest leading-none mb-1">{label}</p>
      <p className="text-lg font-bold font-mono text-emerald-400 leading-none">{value}</p>
      <p className="text-[9px] text-slate-500 font-mono mt-1">{sub}</p>
    </div>
  );
}

function DataPoint({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center border-b border-sto-cardBorder pb-3">
      <span className="text-xs font-semibold text-sto-muted">{label}</span>
      <span className="text-sm font-bold text-sto-text font-mono">{value}</span>
    </div>
  );
}

// ── AI Analyst Component ──────────────────────────────────────────────────────
// State is now LIFTED into the parent. This component only renders.

interface AITerminalProps {
  symbol: string;
  streamData: string;
  setStreamData: (fn: (prev: string) => string) => void;
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;
  hasStarted: boolean;
  setHasStarted: (v: boolean) => void;
  scanningPhase: boolean;
  setScanningPhase: (v: boolean) => void;
  chatHistory: { role: string; content: string }[];
  setChatHistory: (fn: (prev: { role: string; content: string }[]) => { role: string; content: string }[]) => void;
  isChatting: boolean;
  setIsChatting: (v: boolean) => void;
  triggerUrl?: string | null;
  onTriggerUrlProcessed?: () => void;
  triggerUpload?: string | null;
  onTriggerUploadProcessed?: () => void;
}

function AIAnalystTerminal({ symbol, streamData, setStreamData, isStreaming, setIsStreaming, hasStarted, setHasStarted, scanningPhase, setScanningPhase, chatHistory, setChatHistory, isChatting, setIsChatting, triggerUrl, onTriggerUrlProcessed, triggerUpload, onTriggerUploadProcessed }: AITerminalProps) {
  const [chatInput, setChatInput] = useState("");
  const [activeUpload, setActiveUpload] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const processedTriggerRef = useRef<string | null>(null);
  const processedUploadRef = useRef<string | null>(null);

  useEffect(() => {
    if (triggerUrl && triggerUrl !== processedTriggerRef.current) {
      processedTriggerRef.current = triggerUrl;
      // Don't restart the terminal; just send the URL to the chat.
      if (!hasStarted) {
        setHasStarted(true);
      }
      handleChatSubmit(null, `Deep dive into this source: ${triggerUrl}. Tell me the key takeaways, specific financial impacts, and potential risks mentioned in this document.`);
      onTriggerUrlProcessed?.();
    }
  }, [triggerUrl]);

  useEffect(() => {
    if (triggerUpload && triggerUpload !== processedUploadRef.current) {
      processedUploadRef.current = triggerUpload;
      setActiveUpload(triggerUpload);
      if (!hasStarted) {
        setHasStarted(true);
      }
      handleChatSubmit(null, "I have uploaded a new document. Please read it and summarize the core thesis, relevant metrics, and any red flags or catalysts present.");
      onTriggerUploadProcessed?.();
    }
  }, [triggerUpload]);

  useEffect(() => {
    if (scrollRef.current && (isStreaming || isChatting)) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [streamData, isStreaming, isChatting]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsChatting(true);
    setChatHistory(prev => [...prev, { role: "user", content: `[Parsing ${file.name}...]` }]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch(api.llmUploadUrl(symbol), {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();
      
      if (data.full_text) {
        setStreamData((prev: string) => prev + `\n\n---\n\n**SYSTEM >** Upload successful: ${file.name}. Document is now in context.\n\n`);
        setActiveUpload(data.full_text);
        // Start a chat turn to analyze it immediately without wiping history
        handleChatSubmit(null, "Please analyze the document I just uploaded and provide a detailed breakdown of its contents.");
      } else {
        setStreamData((prev: string) => prev + `\n\n**Error:** Could not extract text from ${file.name}.\n\n`);
      }
    } catch (err) {
      setStreamData((prev: string) => prev + `\n\n**Error:** Failed to upload file.\n\n`);
    } finally {
      setIsChatting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const startAnalysis = async (manualUrl?: string, uploadedContent?: string) => {
    setScanningPhase(true);
    setHasStarted(true);
    setStreamData(() => "");
    setChatHistory(() => []);

    setTimeout(async () => {
      setScanningPhase(false);
      setIsStreaming(true);

      try {
        const response = await fetch(api.llmAnalyzeStreamUrl(symbol), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            manual_url: manualUrl,
            uploaded_content: uploadedContent 
          })
        });

        if (!response.body) return;
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullReport = "";
        
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") {
                setIsStreaming(false);
                break;
              }
              try {
                const parsed = JSON.parse(data);
                if (parsed.token) {
                  const content = parsed.token.replace(/\\n/g, '\n');
                  fullReport += content;
                  setStreamData((prev: string) => prev + content);
                }
              } catch (e) { /* ignore */ }
            }
          }
        }
        setChatHistory(() => [{ role: "assistant", content: fullReport }]);
        setIsStreaming(false);
      } catch (err) {
        console.error("Analysis error:", err);
        setIsStreaming(false);
        setStreamData((prev: string) => prev + "\n\n**Error:** Session failed. Check server connection.");
      }
    }, 2500);
  };

  const handleChatSubmit = async (e: React.FormEvent | null, forcedMessage?: string) => {
    if (e) e.preventDefault();
    const message = forcedMessage || chatInput.trim();
    if (!message || isChatting || isStreaming) return;

    const userMessage = message;
    const newHistory = [...chatHistory, { role: "user", content: userMessage }];
    setChatHistory(() => newHistory);
    setChatInput("");
    setIsChatting(true);
    setStreamData((prev: string) => prev + `\n\n---\n\n**YOU >** ${userMessage}\n\n`);

    try {
      const response = await fetch(api.llmChatStreamUrl(symbol), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          history: newHistory,
          uploaded_content: activeUpload 
        })
      });
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantResponse = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              if (parsed.token) {
                const content = parsed.token.replace(/\\n/g, '\n');
                assistantResponse += content;
                setStreamData((prev: string) => prev + content);
              }
            } catch (e) { /* ignore parse errors */ }
          }
        }
      }
      setChatHistory((prev) => [...prev, { role: "assistant", content: assistantResponse }]);
      setIsChatting(false);
    } catch (err) {
      console.error("Chat error:", err);
      setIsChatting(false);
      setStreamData((prev: string) => prev + "\n\n**Error:** Follow-up failed. Check server logs.");
    }
  };

  if (!hasStarted) {
    return (
      <div className="relative overflow-hidden rounded-xl border border-sto-accent/30 bg-sto-card p-10 group shadow-2xl transition-all duration-500 hover:border-sto-accent/60">
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(#0ea5e9_0.5px,transparent_0.5px)] [background-size:16px_16px]"></div>
        <div className="relative z-10 flex flex-col items-center text-center">
          <div className="mb-6 relative">
            <div className="w-20 h-20 bg-sto-accent/5 rounded-2xl flex items-center justify-center border border-sto-accent/20 rotate-3 group-hover:rotate-6 transition-transform duration-500">
               <span className="text-4xl filter drop-shadow-lg">📡</span>
            </div>
            <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 border-2 border-sto-card rounded-full animate-pulse"></div>
          </div>
          <h3 className="text-2xl font-bold text-sto-text mb-3 tracking-tight">Institutional Research Engine</h3>
          <p className="text-sto-muted max-w-lg mb-8 leading-relaxed text-sm">
            Synthesize market data, SEC filings, news, Reddit sentiment, and congressional trades into an investment memo using <span className="text-sto-accent font-mono">Llama-3.2</span>.
          </p>
          <div className="flex flex-wrap justify-center gap-3 mb-10 text-[10px] font-mono">
             <div className="animate-pulse flex items-center gap-2 px-3 py-1.5 rounded-md bg-sto-bg border border-emerald-500/20 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> FEED: {symbol} // LIVE
             </div>
             {["QUANT_MOD", "SEC_SCAN", "REDDIT_PULSE", "CONGRESS_WATCH"].map(tag => (
               <div key={tag} className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-sto-bg border border-sto-cardBorder text-sto-muted">
                  <span className="w-1.5 h-1.5 rounded-full bg-sto-accent"></span> {tag}
               </div>
             ))}
          </div>
          <button 
            onClick={() => startAnalysis()} 
            className="group relative inline-flex items-center gap-3 bg-sto-accent text-white px-8 py-4 rounded-xl font-bold hover:bg-sto-accent/90 transition-all shadow-[0_0_20px_rgba(14,165,233,0.3)] hover:shadow-[0_0_30px_rgba(14,165,233,0.5)] active:scale-95"
          >
            <span>Execute Intelligence Report</span>
            <span className="group-hover:translate-x-1 transition-transform">→</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-slate-700/50 bg-[#0B0E14] rounded-xl overflow-hidden flex flex-col shadow-2xl h-[650px] transition-all duration-500">
      {/* Terminal Header */}
      <div className="bg-[#151921] px-5 py-3 border-b border-slate-800 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#FF5F56]"></div>
            <div className="w-3 h-3 rounded-full bg-[#FFBD2E]"></div>
            <div className="w-3 h-3 rounded-full bg-[#27C93F]"></div>
          </div>
          <div className="h-4 w-px bg-slate-700 ml-2"></div>
          <span className="text-[11px] font-mono font-bold tracking-widest text-slate-500 uppercase">TERMINAL // {symbol}</span>
        </div>
        <div className="flex items-center gap-4">
          {!(scanningPhase || isStreaming || isChatting) && (
            <button onClick={() => { setHasStarted(false); setStreamData(() => ""); setChatHistory(() => []); }} className="text-[10px] font-bold text-slate-500 hover:text-sto-accent transition-colors uppercase tracking-tighter">Reset</button>
          )}
          <div className="flex items-center gap-2 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
            <span className={`w-1.5 h-1.5 rounded-full ${isStreaming || scanningPhase || isChatting ? 'bg-emerald-500 animate-pulse' : 'bg-slate-700'}`}></span>
            <span className="text-[10px] font-mono text-slate-400 uppercase">
              {scanningPhase ? "SCANNING" : (isStreaming || isChatting) ? "STREAMING" : "ACTIVE"}
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Main Content Area */}
        <div ref={scrollRef} className="flex-1 p-8 overflow-y-auto font-mono text-[13px] leading-relaxed text-slate-300 custom-scrollbar relative">
          {scanningPhase && (
            <div className="flex flex-col gap-4 animate-in fade-in duration-700">
               <p className="text-emerald-400">-{">"} Handshake with Ollama node...</p>
               <p className="text-slate-500">-{">"} Pulling YFinance market data...</p>
               <p className="text-slate-500">-{">"} Scraping Reddit sentiment for {symbol}...</p>
               <p className="text-slate-500">-{">"} Checking congressional trades...</p>
               <p className="text-emerald-500/80">-{">"} Reading full content from top sources...</p>
               <p className="text-slate-500">-{">"} Parsing SEC disclosures...</p>
               <div className="flex items-center gap-2 mt-2">
                  <div className="w-2 h-2 bg-emerald-500 animate-ping"></div>
                  <span className="text-emerald-500">Building context window for {symbol}...</span>
               </div>
            </div>
          )}
          {!scanningPhase && (
            <div className="prose prose-invert max-w-none prose-slate prose-headings:font-bold prose-headings:tracking-tight prose-headings:text-slate-100 prose-p:text-slate-400 prose-strong:text-emerald-400 prose-code:text-emerald-300 prose-li:text-slate-400 mb-20">
              <ReactMarkdown>{streamData || "Initializing research stream..."}</ReactMarkdown>
              {(isStreaming || isChatting) && <span className="inline-block w-2 h-4 bg-emerald-500 ml-1 animate-pulse align-middle"></span>}
            </div>
          )}
        </div>
        {/* Chat Input Interface */}
        {!scanningPhase && !isStreaming && hasStarted && (
          <div className="p-4 bg-[#151921] border-t border-slate-800">
            <form onSubmit={handleChatSubmit} className="relative flex items-center gap-2">
              <span className="absolute left-4 text-emerald-500 font-mono text-sm">-{">"}</span>
              <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} disabled={isChatting}
                placeholder={isChatting ? "Analyst is typing..." : "Ask a follow-up (e.g. 'Summarize the risks' or 'What about Reddit sentiment?')..."}
                className="w-full bg-[#0B0E14] border border-slate-800 rounded-lg py-3 pl-10 pr-24 text-sm font-mono text-slate-200 placeholder:text-slate-700 focus:outline-none focus:border-sto-accent transition-all" />
              
              <div className="absolute right-2 flex items-center">
                {/* File Upload Button */}
                <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.md,.html" />
                <button type="button" onClick={() => fileInputRef.current?.click()} disabled={isChatting} className="p-2 text-slate-500 hover:text-emerald-400 disabled:opacity-30 transition-colors" title="Upload Document for Context">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
                </button>

                {/* Send Button */}
                <button type="submit" disabled={isChatting || !chatInput.trim()} className="p-2 text-slate-500 hover:text-sto-accent disabled:opacity-30 transition-colors" title="Send">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
      {/* Footer */}
      <div className="bg-[#0B0E14] px-5 py-2 border-t border-slate-800/50 flex justify-between items-center text-[10px] font-mono text-slate-600">
         <span>LOCAL_AI // llama3.2:3b</span>
         <span className="animate-pulse">SESSION_ACTIVE</span>
         <span>UTC {new Date().toISOString().split('T')[1].split('.')[0]}</span>
      </div>
    </div>
  );
}


// ── Main component ────────────────────────────────────────────────────────────

function SentimentContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const symbolParam = (searchParams.get("symbol") || "AAPL").toUpperCase();
  const [searchInput, setSearchInput] = useState(symbolParam);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const [research, setResearch] = useState<StockResearch | null>(null);
  const [loadingResearch, setLoadingResearch] = useState(true);
  const [articlePage, setArticlePage] = useState(1);
  const ARTICLES_PER_PAGE = 10;

  // ── CHART STATE ─────────────────────────────────────────────────────────────
  const [chartRange, setChartRange] = useState("1mo");
  const [dynamicChartData, setDynamicChartData] = useState<{date: string, price: number}[]>([]);
  const [isChartLoading, setIsChartLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  // ── LIFTED AI STATE (persists across tab switches) ────────────────────────
  const [aiStreamData, setAiStreamData] = useState("");
  const [aiIsStreaming, setAiIsStreaming] = useState(false);
  const [aiHasStarted, setAiHasStarted] = useState(false);
  const [aiScanningPhase, setAiScanningPhase] = useState(false);
  const [aiChatHistory, setAiChatHistory] = useState<{role: string, content: string}[]>([]);
  const [aiIsChatting, setAiIsChatting] = useState(false);
  const [pendingDeepDive, setPendingDeepDive] = useState<string | null>(null);
  const [pendingUpload, setPendingUpload] = useState<string | null>(null);

  // Fetch symbol-specific data
  useEffect(() => {
    setSearchInput(symbolParam);
    setLoadingResearch(true);
    setArticlePage(1);
    setActiveTab("overview");
    // Reset AI state on symbol change
    setAiStreamData("");
    setAiIsStreaming(false);
    setAiHasStarted(false);
    setAiScanningPhase(false);
    setAiChatHistory([]);
    setAiIsChatting(false);
    setPendingDeepDive(null);
    setPendingUpload(null);

    api
      .stockResearch(symbolParam)
      .then((data) => setResearch(data))
      .catch((e) => console.error("Research error:", e))
      .finally(() => setLoadingResearch(false));
  }, [symbolParam]);

  // Fetch dynamic chart history when symbol or timeframe changes
  useEffect(() => {
     setIsChartLoading(true);
     api.fetchChartData(symbolParam, chartRange)
       .then(res => {
          if (res.chart_data && res.chart_data.length > 0) {
              setDynamicChartData(res.chart_data);
          } else {
              // fallback to market data if API fails to yield results
              if (research?.market_data?.chart_data) {
                  setDynamicChartData(research.market_data.chart_data);
              }
          }
       })
       .catch(e => console.error("Chart error:", e))
       .finally(() => setIsChartLoading(false));
  }, [symbolParam, chartRange]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = searchInput.trim();
    if (!q) return;
    
    setIsSearching(true);
    try {
      const res = await api.searchTicker(q);
      const symbol = res.symbol || q.toUpperCase();
      setSearchInput(symbol);
      router.push(`/sentiment?symbol=${symbol}`);
    } catch {
      router.push(`/sentiment?symbol=${q.toUpperCase()}`);
    } finally {
      setIsSearching(false);
    }
  }

  // Pagination for articles
  const allArticles = research?.articles ?? [];
  const pagedArticles = allArticles.slice(
    (articlePage - 1) * ARTICLES_PER_PAGE,
    articlePage * ARTICLES_PER_PAGE
  );
  const totalArticlePages = Math.ceil(allArticles.length / ARTICLES_PER_PAGE);

  const market = research?.market_data;
  const isUp = market ? market.change >= 0 : true;

  return (
    <div className="space-y-8">

      {/* ── Top Bar / Search ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-4 items-start justify-between">
        <form onSubmit={handleSearch} className="flex gap-2 w-full sm:w-auto relative">
          <input type="text" value={searchInput} onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search Company or Ticker (e.g. Apple or AAPL)"
            disabled={isSearching}
            className="w-full sm:w-[320px] rounded-lg border border-sto-cardBorder bg-sto-card px-4 py-3 text-sm text-sto-text placeholder:text-sto-muted focus:outline-none focus:ring-2 focus:ring-sto-accent/30 font-mono shadow-sm disabled:opacity-70 transition-all" />
          {isSearching && (
            <div className="absolute right-24 top-1/2 -translate-y-1/2">
               <div className="w-4 h-4 border-2 border-sto-accent border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
          <button type="submit" disabled={isSearching} className="rounded-lg bg-sto-accent text-white px-6 py-3 font-semibold hover:bg-sto-accent/90 transition shadow-sm disabled:opacity-50">
            {isSearching ? '...' : 'Search'}
          </button>
        </form>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto mt-2 sm:mt-0">
          {POPULAR.map((s) => (
            <Link key={s} href={`/sentiment?symbol=${s}`}
              className={`font-mono text-xs font-medium px-3 py-1.5 rounded-full border transition ${s === symbolParam ? "bg-sto-accent text-white border-transparent" : "border-sto-cardBorder bg-sto-card text-sto-text hover:border-sto-accent/40"}`}>{s}</Link>
          ))}
        </div>
      </div>

      {loadingResearch && <div className="h-64 rounded-sto-lg border border-sto-cardBorder bg-sto-card p-5 animate-pulse" />}

      {/* ── Market Data Header ────────────────────────────────────────────── */}
      {!loadingResearch && research && market && (
        <div className="bg-sto-card border border-sto-cardBorder rounded-xl shadow-sm p-6">
           <div className="flex flex-col md:flex-row justify-between gap-6">
              <div className="flex-1">
                 <div className="flex items-center gap-3 mb-2">
                    <h1 className="text-4xl font-bold font-mono tracking-tight text-sto-text">{research.ticker}</h1>
                    <span className="text-sm font-medium px-2 py-0.5 rounded bg-sto-bg text-sto-muted border border-sto-cardBorder">{market.sector || "Equity"}</span>
                 </div>
                 <h2 className="text-lg text-sto-muted font-medium mb-6">{research.company}</h2>
                 <div className="flex items-end gap-3 font-mono tracking-tight">
                    <span className="text-5xl font-bold text-sto-text">
                      {market.price !== null && market.price !== undefined ? `$${market.price.toFixed(2)}` : "-"}
                    </span>
                    <span className={`text-xl font-semibold mb-1 flex items-center ${isUp ? 'text-emerald-500' : 'text-red-500'}`}>
                       {isUp ? '▲' : '▼'} {Math.abs(market.change).toFixed(2)} ({Math.abs(market.change_percent).toFixed(2)}%)
                    </span>
                 </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-x-8 gap-y-4 text-sm mt-4 md:mt-0">
                 <div><p className="text-sto-muted text-xs uppercase tracking-wider mb-1">Market Cap</p><p className="font-semibold font-mono text-sto-text">{formatLargeNumber(market.market_cap)}</p></div>
                 <div><p className="text-sto-muted text-xs uppercase tracking-wider mb-1">P/E Ratio</p><p className="font-semibold font-mono text-sto-text">{market.pe_ratio !== null && market.pe_ratio !== undefined ? market.pe_ratio.toFixed(2) : "-"}</p></div>
                 <div><p className="text-sto-muted text-xs uppercase tracking-wider mb-1">Div Yield</p><p className="font-semibold font-mono text-sto-text">{market.dividend_yield ? (market.dividend_yield * 100).toFixed(2) + "%" : "-"}</p></div>
                 <div><p className="text-sto-muted text-xs uppercase tracking-wider mb-1">Volume</p><p className="font-semibold font-mono text-sto-text">{formatLargeNumber(market.volume)}</p></div>
                 <div><p className="text-sto-muted text-xs uppercase tracking-wider mb-1">52W High</p><p className="font-semibold font-mono text-sto-text">{market.fifty_two_week_high !== null ? `$${market.fifty_two_week_high?.toFixed(2)}` : "-"}</p></div>
                 <div><p className="text-sto-muted text-xs uppercase tracking-wider mb-1">52W Low</p><p className="font-semibold font-mono text-sto-text">{market.fifty_two_week_low !== null ? `$${market.fifty_two_week_low?.toFixed(2)}` : "-"}</p></div>
              </div>
           </div>

           {/* Modern Trend Graph */}
           {(dynamicChartData.length > 0 || (market.chart_data && market.chart_data.length > 0)) && (() => {
             const dataToUse = dynamicChartData.length > 0 ? dynamicChartData : market.chart_data;
             const isChartUp = dataToUse.length >= 2 ? dataToUse[dataToUse.length - 1].price >= dataToUse[0].price : true;
             
             return (
               <div className="mt-8 pt-6 border-t border-sto-cardBorder">
                  <div className="flex flex-wrap items-center justify-between mb-6">
                    <p className="text-xs font-semibold uppercase tracking-wider text-sto-muted">Historical Price Trend</p>
                    <div className="flex gap-1 bg-sto-bg rounded-lg p-1 border border-sto-cardBorder">
                      {["1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y", "5y", "max"].map((rng) => (
                        <button 
                          key={rng}
                          onClick={() => setChartRange(rng)}
                          className={`text-[10px] font-mono px-3 py-1.5 rounded-md transition-colors ${chartRange === rng ? "bg-sto-card border border-sto-cardBorder text-sto-text shadow" : "text-sto-muted hover:text-sto-text"}`}
                        >
                          {rng.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  <div className="h-64 w-full" style={{ position: 'relative', zIndex: 0 }}>
                     {isChartLoading && (
                       <div className="absolute inset-0 flex items-center justify-center bg-sto-card/50 backdrop-blur-[2px] z-10 rounded-xl">
                         <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                       </div>
                     )}
                     <ResponsiveContainer width="100%" height={240}>
                       <AreaChart data={dataToUse} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                         <defs>
                           <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                             <stop offset="5%" stopColor={isChartUp ? "#10b981" : "#ef4444"} stopOpacity={0.4}/>
                             <stop offset="95%" stopColor={isChartUp ? "#10b981" : "#ef4444"} stopOpacity={0}/>
                           </linearGradient>
                         </defs>
                         <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.2} />
                         <XAxis dataKey="date" hide />
                         <YAxis domain={['auto', 'auto']} hide />
                         <Tooltip
                           contentStyle={{ 
                             backgroundColor: '#1E293B', 
                             border: `1px solid ${isChartUp ? '#10b98160' : '#ef444460'}`, 
                             borderRadius: '12px', 
                             color: '#f8fafc', 
                             boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
                             padding: '12px'
                           }}
                           labelStyle={{ color: '#94a3b8', fontSize: '11px', fontWeight: 500, marginBottom: '6px' }}
                           itemStyle={{ color: isChartUp ? '#10b981' : '#ef4444', fontWeight: 800, fontSize: '18px' }}
                           labelFormatter={(label) => {
                             if (!label) return '';
                             const dt = new Date(label);
                             if (chartRange === "1d" || chartRange === "5d") {
                               return dt.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                             }
                             return dt.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
                           }}
                           formatter={(value: any) => [`$${Number(value).toFixed(2)}`, 'Price']}
                         />
                         <Area 
                           type="monotone" 
                           dataKey="price" 
                           stroke={isChartUp ? "#10b981" : "#ef4444"} 
                           strokeWidth={3}
                           fillOpacity={1} 
                           fill="url(#colorPrice)" 
                         />
                       </AreaChart>
                     </ResponsiveContainer>
                  </div>
               </div>
             );
           })()}
        </div>
      )}

      {/* ── Tab navigation ────────────────────────────────────────────────── */}
      <div className="border-b border-sto-cardBorder mt-8">
        <div className="flex gap-1 overflow-x-auto">
          <TabButton active={activeTab === "overview"} label="AI Report & Overview" onClick={() => setActiveTab("overview")} />
          <TabButton active={activeTab === "articles"} label="News" count={research?.total_articles} onClick={() => setActiveTab("articles")} />
          <TabButton active={activeTab === "filings"} label="SEC Filings" count={research?.total_filings} onClick={() => setActiveTab("filings")} />
          <TabButton active={activeTab === "financials"} label="Financials" onClick={() => setActiveTab("financials")} />
          <TabButton active={activeTab === "social"} label="Social Media" count={research?.total_reddit} onClick={() => setActiveTab("social")} />
          <TabButton active={activeTab === "politics"} label="Politics" count={research?.total_congress} onClick={() => setActiveTab("politics")} />
        </div>
      </div>

      {/* ── Tab content ───────────────────────────────────────────────────── */}

      {/* Overview tab */}
      {activeTab === "overview" && research && (
        <div className="space-y-6 animate-in fade-in duration-500">
          <div>
            <h3 className="text-xs uppercase tracking-wider font-semibold text-sto-muted mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span> Live LLM Analysis
            </h3>
            <AIAnalystTerminal
              symbol={research.ticker}
              streamData={aiStreamData} setStreamData={(fn) => setAiStreamData(fn)}
              isStreaming={aiIsStreaming} setIsStreaming={setAiIsStreaming}
              hasStarted={aiHasStarted} setHasStarted={setAiHasStarted}
              scanningPhase={aiScanningPhase} setScanningPhase={setAiScanningPhase}
              chatHistory={aiChatHistory} setChatHistory={(fn) => setAiChatHistory(fn)}
              isChatting={aiIsChatting} setIsChatting={setAiIsChatting}
              triggerUrl={pendingDeepDive}
              onTriggerUrlProcessed={() => setPendingDeepDive(null)}
              triggerUpload={pendingUpload}
              onTriggerUploadProcessed={() => setPendingUpload(null)}
            />
          </div>
          {market?.description && (
             <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-6 shadow-sm">
                <h3 className="text-xs uppercase tracking-wider font-semibold text-sto-muted mb-3">About the Company</h3>
                <p className="text-sm leading-relaxed text-sto-text max-h-40 overflow-y-auto pr-4 custom-scrollbar">{market.description}</p>
             </div>
          )}
        </div>
      )}

      {/* Financials tab */}
      {activeTab === "financials" && research && market && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-8">
           <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Scorecard */}
              <div className="lg:col-span-1 rounded-xl border border-emerald-500/20 bg-sto-card p-6 shadow-xl relative overflow-hidden h-fit">
                 <div className="absolute top-0 right-0 p-4 opacity-5"><span className="text-6xl font-bold font-mono text-emerald-500">HF</span></div>
                 <h3 className="text-sm font-bold text-sto-text mb-6 flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Analyst Scorecard</h3>
                 <div className="space-y-6">
                    <ScoreItem label="Valuation Tier" value={market.pe_ratio && market.pe_ratio > 25 ? (market.pe_ratio > 50 ? "PREMIUM" : "ELEVATED") : "MODERATE"} sub={`P/E: ${market.pe_ratio?.toFixed(1) || 'N/A'}`} />
                    <ScoreItem label="Volatility" value={market.beta ? (market.beta > 1.3 ? "AGGRESSIVE" : market.beta < 0.7 ? "DEFENSIVE" : "MARKET") : "N/A"} sub={`Beta: ${market.beta?.toFixed(2) || 'N/A'}`} />
                    <ScoreItem label="Profitability" value={market.profit_margins && market.profit_margins > 0.20 ? "ELITE" : market.profit_margins && market.profit_margins > 0.10 ? "STRONG" : "AVERAGE"} sub={`Net Margin: ${formatPercent(market.profit_margins)}`} />
                    <ScoreItem label="Growth Outlook" value={market.eps_next_year && market.eps_next_year > 0.15 ? "EXPANSIVE" : "STABLE"} sub={`Est. Growth: ${formatPercent(market.eps_next_year)}`} />
                 </div>
              </div>

              {/* Fundamental Grid */}
              <div className="lg:col-span-3 space-y-6">
                 {/* Valuation Multiples */}
                 <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-6 shadow-sm">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-sto-muted mb-6 flex items-center gap-2">
                       <span className="w-1.5 h-1.5 rounded-full bg-sto-accent"></span> Valuation Multiples
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-x-12 gap-y-6">
                       <DataPoint label="P/E Ratio (TTM)" value={market.pe_ratio?.toFixed(2) || "N/A"} />
                       <DataPoint label="Forward P/E" value={market.forward_pe?.toFixed(2) || "N/A"} />
                       <DataPoint label="PEG Ratio" value={market.peg_ratio?.toFixed(2) || "N/A"} />
                       <DataPoint label="Price to Sales" value={market.price_to_sales?.toFixed(2) + "x" || "N/A"} />
                       <DataPoint label="Price to Book" value={market.price_to_book?.toFixed(2) + "x" || "N/A"} />
                       <DataPoint label="Price to FCF" value={market.price_to_free_cash_flow?.toFixed(2) + "x" || "N/A"} />
                       <DataPoint label="EV/EBITDA" value={market.enterprise_to_ebitda?.toFixed(2) + "x" || "N/A"} />
                       <DataPoint label="Enterprise Value" value={formatLargeNumber(market.enterprise_value)} />
                       <DataPoint label="Market Cap" value={formatLargeNumber(market.market_cap)} />
                    </div>
                 </div>

                 <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Profitability */}
                    <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-6 shadow-sm">
                        <h3 className="text-xs uppercase tracking-wider font-bold text-sto-muted mb-6">Efficiency & Margins</h3>
                        <div className="space-y-4">
                           <DataPoint label="Gross Margin" value={formatPercent(market.gross_margin)} />
                           <DataPoint label="Operating Margin" value={formatPercent(market.operating_margins)} />
                           <DataPoint label="Net Profit Margin" value={formatPercent(market.profit_margins)} />
                           <DataPoint label="Return on Equity (ROE)" value={formatPercent(market.return_on_equity)} />
                           <DataPoint label="Return on Assets (ROA)" value={formatPercent(market.return_on_assets)} />
                           <DataPoint label="ROIC" value={formatPercent(market.roic)} />
                        </div>
                    </div>

                    {/* Financial Health */}
                    <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-6 shadow-sm">
                        <h3 className="text-xs uppercase tracking-wider font-bold text-sto-muted mb-6">Balance Sheet & Health</h3>
                        <div className="space-y-4">
                           <DataPoint label="Total Cash" value={formatLargeNumber(market.total_cash)} />
                           <DataPoint label="Free Cash Flow" value={formatLargeNumber(market.free_cash_flow)} />
                           <DataPoint label="Current Ratio" value={market.current_ratio?.toFixed(2) || "N/A"} />
                           <DataPoint label="Quick Ratio" value={market.quick_ratio?.toFixed(2) || "N/A"} />
                           <DataPoint label="Debt to Equity" value={market.debt_to_equity?.toFixed(2) || "N/A"} />
                           <DataPoint label="LT Debt to Equity" value={market.lt_debt_to_equity?.toFixed(2) || "N/A"} />
                        </div>
                    </div>
                 </div>

                 {/* Growth & EPS */}
                 <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-6 shadow-sm">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-sto-muted mb-6 flex items-center gap-2">
                       <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span> Growth & Performance
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-x-12 gap-y-6">
                       <DataPoint label="Revenue (TTM)" value={formatLargeNumber(market.total_revenue)} />
                       <DataPoint label="Net Income (TTM)" value={formatLargeNumber(market.net_income)} />
                       <DataPoint label="EPS (TTM)" value={`$${market.eps_ttm?.toFixed(2) || "N/A"}`} />
                       <DataPoint label="Sales Growth (Q/Q)" value={formatPercent(market.sales_growth_qq)} />
                       <DataPoint label="EPS Growth (Q/Q)" value={formatPercent(market.eps_growth_qq)} />
                       <DataPoint label="Est. Growth (Next Y)" value={formatPercent(market.eps_next_year)} />
                       <DataPoint label="Dividend Yield" value={formatPercent(market.dividend_yield)} />
                       <DataPoint label="Payout Ratio" value={formatPercent(market.payout_ratio)} />
                       <DataPoint label="Target Price" value={market.target_price ? `$${market.target_price.toFixed(2)}` : "N/A"} />
                    </div>
                 </div>
              </div>
           </div>
        </div>
      )}

      {/* Social Media tab */}
      {activeTab === "social" && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-8">
          
          {/* Twitter / Stocktwits section */}
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className="text-2xl">🐦</span>
              <div>
                <h3 className="text-base font-bold text-sto-text">Retail Tweets (StockTwits)</h3>
                <p className="text-xs text-sto-muted">Latest social chatter and retail sentiment</p>
              </div>
            </div>
            
            {!research?.stocktwits_posts?.length ? (
              <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-8 text-center">
                <p className="text-sto-muted text-sm">No recent tweets found for <span className="font-mono font-bold">{symbolParam}</span>.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {research.stocktwits_posts.map((tweet, i) => (
                  <div key={tweet.id || i} className="group rounded-xl border border-sky-500/10 bg-sto-card p-5 hover:border-sky-500/30 transition-all shadow-sm">
                    <div className="flex items-center gap-3 mb-3">
                      {tweet.avatar_url ? (
                        <img src={tweet.avatar_url} alt={tweet.username} className="w-8 h-8 rounded-full bg-slate-800" />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-slate-800" />
                      )}
                      <div>
                        <p className="text-xs font-bold text-sky-400">@{tweet.username}</p>
                        <p className="text-[10px] text-sto-muted">{timeAgo(tweet.created_at)}</p>
                      </div>
                      {tweet.sentiment && (
                        <span className={`ml-auto text-[10px] px-2 py-0.5 rounded font-bold uppercase ${tweet.sentiment === 'Bullish' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                          {tweet.sentiment}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-sto-text leading-snug">{tweet.body}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-sto-cardBorder pt-8" />

          {/* Reddit section */}
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className="text-2xl">📱</span>
              <div>
                <h3 className="text-base font-bold text-sto-text">Reddit Discussions</h3>
                <p className="text-xs text-sto-muted">Trending posts from r/wallstreetbets and r/investing</p>
              </div>
            </div>
            
            {!research?.reddit_posts?.length ? (
              <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-8 text-center">
                <p className="text-sto-muted text-sm">No recent Reddit mentions found for <span className="font-mono font-bold">{symbolParam}</span>.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {research.reddit_posts.map((post, i) => (
                  <a key={i} href={post.url} target="_blank" rel="noopener noreferrer"
                    className="group rounded-xl border border-orange-500/10 bg-sto-card p-5 hover:border-orange-500/30 transition-all shadow-sm hover:shadow-md">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs font-bold text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded">r/{post.subreddit}</span>
                      <span className="text-[10px] text-sto-muted">{formatTimestamp(post.created_utc)}</span>
                    </div>
                    <p className="text-sm font-medium text-sto-text group-hover:text-orange-300 line-clamp-3 leading-snug mb-4">{post.title}</p>
                    <div className="flex items-center gap-4 text-xs text-sto-muted">
                      <span className="flex items-center gap-1">
                        <span className="text-orange-400 font-bold">▲ {post.score}</span>
                      </span>
                      <span>💬 {post.num_comments} comments</span>
                      <span className={`ml-auto font-mono text-[10px] ${post.upvote_ratio > 0.7 ? 'text-emerald-400' : post.upvote_ratio < 0.4 ? 'text-red-400' : 'text-yellow-400'}`}>
                        {(post.upvote_ratio * 100).toFixed(0)}% positive
                      </span>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Politics tab */}
      {activeTab === "politics" && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Header & Stats */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-xl">🏛️</div>
              <div>
                <h3 className="text-base font-bold text-sto-text">Congressional Trading Intelligence</h3>
                <p className="text-xs text-sto-muted">Disclosed trades by US House and Senate members for {symbolParam}</p>
              </div>
            </div>

            {research?.congress_trades?.length ? (
              <div className="flex gap-4">
                <div className="bg-sto-card border border-sto-cardBorder rounded-xl p-3 px-5 flex flex-col items-center">
                  <span className="text-[10px] uppercase tracking-wider text-sto-muted font-bold mb-1">Buy/Sell Ratio</span>
                  <div className="flex items-center gap-2">
                    <span className="text-emerald-500 font-bold">
                      {research.congress_trades.filter(t => t.trade_type === 'buy').length}
                    </span>
                    <span className="text-sto-muted">/</span>
                    <span className="text-red-500 font-bold">
                      {research.congress_trades.filter(t => t.trade_type === 'sell').length}
                    </span>
                  </div>
                </div>
                <div className="bg-sto-card border border-sto-cardBorder rounded-xl p-3 px-5 flex flex-col items-center">
                  <span className="text-[10px] uppercase tracking-wider text-sto-muted font-bold mb-1">Sentiment</span>
                  <span className={`font-bold ${
                    research.congress_trades.filter(t => t.trade_type === 'buy').length > research.congress_trades.filter(t => t.trade_type === 'sell').length 
                    ? 'text-emerald-500' : 'text-amber-500'
                  }`}>
                    {research.congress_trades.filter(t => t.trade_type === 'buy').length > research.congress_trades.filter(t => t.trade_type === 'sell').length ? 'BULLISH' : 'CAUTIOUS'}
                  </span>
                </div>
              </div>
            ) : null}
          </div>

          {!research?.congress_trades?.length ? (
            <div className="rounded-2xl border border-dashed border-sto-cardBorder bg-sto-card/30 p-16 text-center shadow-inner">
              <span className="text-5xl mb-6 block grayscale opacity-30">⚖️</span>
              <p className="text-sto-text text-lg font-semibold">No recent political exposure</p>
              <p className="text-sto-muted text-sm max-w-md mx-auto mt-2">
                Lawmakers haven't disclosed any major trades in <span className="font-mono text-sto-accent">{symbolParam}</span> in the last 180 days. 
                This often suggests low political volatility for this asset.
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {research.congress_trades.map((trade, i) => (
                <div key={i} className="group relative overflow-hidden rounded-xl border border-sto-cardBorder bg-sto-card p-5 hover:border-sto-accent/50 hover:shadow-lg hover:shadow-indigo-500/5 transition-all">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                    {/* Badge Column */}
                    <div className="flex items-center gap-4 flex-1">
                      <div className={`relative w-14 h-14 rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-lg ring-4 ring-sto-bg ${trade.party === 'R' ? 'bg-gradient-to-br from-red-500 to-red-700' : trade.party === 'D' ? 'bg-gradient-to-br from-blue-500 to-blue-700' : 'bg-gradient-to-br from-slate-500 to-slate-700'}`}>
                        {trade.party}
                        <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-sto-card rounded-full border border-sto-cardBorder flex items-center justify-center">
                          <div className={`w-3 h-3 rounded-full ${trade.trade_type === 'buy' ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                        </div>
                      </div>
                      
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="text-base font-bold text-sto-text truncate">{trade.politician}</h4>
                          <span className={`hidden sm:inline-block text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-tighter ${trade.trade_type === 'buy' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                            {trade.trade_type}
                          </span>
                        </div>
                        <p className="text-xs text-sto-muted font-medium mt-0.5 flex items-center gap-2">
                          <span className="text-sto-accent">Committees:</span>
                          <span className="truncate">{trade.committee || "Member of Congress"}</span>
                        </p>
                        <div className="mt-2 flex items-center gap-4 text-[10px] text-sto-muted font-mono uppercase tracking-widest">
                          <span>📅 {trade.trade_date}</span>
                          <span>💰 {trade.amount_range}</span>
                        </div>
                      </div>
                    </div>

                    {/* Impact Score / Action Column */}
                    <div className="flex items-center justify-between sm:flex-col sm:items-end gap-3 pt-4 sm:pt-0 border-t sm:border-t-0 border-sto-cardBorder/50">
                      <div className="flex flex-col items-end">
                        <span className="text-[10px] text-sto-muted font-bold uppercase tracking-tighter mb-1">Impact Score</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-1.5 bg-sto-bg rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${(trade.impact_score || 50) > 80 ? 'bg-emerald-500' : (trade.impact_score || 50) > 50 ? 'bg-indigo-500' : 'bg-red-500'}`}
                              style={{ width: `${trade.impact_score || 0}%` }}
                            ></div>
                          </div>
                          <span className="text-xs font-mono font-bold text-sto-text">{trade.impact_score || 'N/A'}</span>
                        </div>
                      </div>
                      
                      <div className="sm:hidden text-xs font-bold uppercase text-sto-accent">
                        View Filing →
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              
              <div className="mt-4 p-4 rounded-xl bg-amber-500/5 border border-amber-500/10 flex gap-3">
                <span className="text-xl">⚠️</span>
                <p className="text-[10px] leading-relaxed text-amber-200/60 font-medium">
                  <strong>DISCLAIMER:</strong> Congressional trading data is delayed by 30-45 days per the STOCK Act. Recent trades shown may reflect past legislative insight. Politics Intelligence should be used in conjunction with technical and fundamental analysis.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Articles tab */}
      {activeTab === "articles" && (
        <div>
          {loadingResearch ? null : allArticles.length === 0 ? (
            <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-8 text-center">
              <p className="text-sto-muted text-sm">No recent articles mention <span className="font-mono font-semibold">{symbolParam}</span>.</p>
            </div>
          ) : (
            <>
              <div className="divide-y divide-sto-cardBorder rounded-xl border border-sto-cardBorder bg-sto-card overflow-hidden shadow-sm">
                {pagedArticles.map((a: NewsArticle) => (
                  <div key={a.id} className="p-5 hover:bg-sto-bg transition group">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <a href={a.url} target="_blank" rel="noopener noreferrer" className="text-base font-semibold text-sto-text group-hover:text-sto-accent transition-colors line-clamp-2 leading-snug">{a.title}</a>
                        {a.description && <p className="mt-2 text-sm text-sto-muted line-clamp-2">{a.description}</p>}
                        <div className="mt-3 flex items-center gap-3 flex-wrap">
                          <span className="text-xs text-sto-text font-semibold bg-sto-bg px-2 py-1 rounded border border-sto-cardBorder">{a.source}</span>
                          <span className="text-xs text-sto-muted">{timeAgo(a.published_at)}</span>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2 shrink-0">
                        <button 
                          onClick={() => {
                            setPendingDeepDive(a.url);
                            setActiveTab("overview");
                          }}
                          className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded hover:bg-emerald-500/20 transition flex items-center gap-2"
                        >
                          <span>🧠</span> Deep Dive
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {totalArticlePages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-6">
                  <button disabled={articlePage <= 1} onClick={() => setArticlePage((p) => p - 1)} className="px-4 py-2 text-sm font-semibold rounded-lg border border-sto-cardBorder bg-sto-card text-sto-text hover:border-sto-accent/40 transition disabled:opacity-40 disabled:cursor-not-allowed">← Previous</button>
                  <span className="text-sm font-mono text-sto-muted px-4">{articlePage} / {totalArticlePages}</span>
                  <button disabled={articlePage >= totalArticlePages} onClick={() => setArticlePage((p) => p + 1)} className="px-4 py-2 text-sm font-semibold rounded-lg border border-sto-cardBorder bg-sto-card text-sto-text hover:border-sto-accent/40 transition disabled:opacity-40 disabled:cursor-not-allowed">Next →</button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* SEC Filings tab */}
      {activeTab === "filings" && (
        <div>
          {loadingResearch ? null : !research || research.filings.length === 0 ? (
            <div className="rounded-xl border border-sto-cardBorder bg-sto-card p-8 text-center">
              <p className="text-sto-muted text-sm">No SEC filings found for <span className="font-mono font-semibold">{symbolParam}</span>.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="divide-y divide-sto-cardBorder rounded-xl border border-sto-cardBorder bg-sto-card overflow-hidden shadow-sm">
                {research.filings.map((f: SECFiling, i: number) => (
                  <FilingRow key={i} filing={f} onDeepDive={(url) => {
                    setPendingDeepDive(url);
                    setActiveTab("overview");
                  }} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SentimentPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse flex flex-col items-center">
           <div className="w-12 h-12 border-4 border-sto-accent/20 border-t-sto-accent rounded-full animate-spin mb-4"></div>
           <p className="text-sto-muted font-mono uppercase tracking-widest text-sm">Connecting to Terminal...</p>
        </div>
      </div>
    }>
      <SentimentContent />
    </Suspense>
  );
}
