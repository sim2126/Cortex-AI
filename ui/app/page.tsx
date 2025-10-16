"use client";

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Search, BrainCircuit, CheckCircle, AlertTriangle, Database, ArrowRight, Activity, Cpu, Radio, Upload, BookOpen, Link, XCircle, RefreshCw } from "lucide-react";

type ReasoningStep = {
  node: string;
  status: 'running' | 'finished' | 'error';
};

type UploadStatus = {
  inProgress: boolean;
  message: string;
  isError: boolean;
};

export default function Home() {
  const [question, setQuestion] = useState<string>('');
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([]);
  const [finalAnswer, setFinalAnswer] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({ inProgress: false, message: '', isError: false });
  const [knowledgeSources, setKnowledgeSources] = useState<string[]>([]);
  const [links, setLinks] = useState<string>('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const fetchKnowledgeSources = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/knowledge/sources');
      if (!response.ok) {
        console.error("Failed to fetch knowledge sources");
        setKnowledgeSources([]);
        return;
      }
      const sources = await response.json();
      setKnowledgeSources(sources);
    } catch (e) {
      console.error("Error fetching knowledge sources:", e);
      setKnowledgeSources([]);
    }
  };

  useEffect(() => {
    fetchKnowledgeSources();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const gridSize = 50;
    let offset = 0;

    let animationId: number;
    const animate = () => {
      if(!ctx) return;
      ctx.fillStyle = 'rgba(15, 23, 42, 1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = 'rgba(51, 65, 85, 0.3)';
      ctx.lineWidth = 1;

      for (let x = (offset % gridSize) - gridSize; x < canvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }

      for (let y = (offset % gridSize) - gridSize; y < canvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      offset += 0.5;
      animationId = requestAnimationFrame(animate);
    };

    animate();

    const handleResize = () => {
      if(canvas) {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const nodeToConfig = (node: string) => {
    const configs = {
      planner: { icon: <Search className="h-5 w-5" />, label: 'Query Planner' },
      retriever: { icon: <Database className="h-5 w-5" />, label: 'Context Retriever' },
      responder: { icon: <BrainCircuit className="h-5 w-5" />, label: 'Response Engine' },
    };
    return configs[node as keyof typeof configs] || { icon: <Cpu className="h-5 w-5" />, label: node };
  };

  const handleSubmit = async () => {
    if (!question || isLoading) return;
    setIsLoading(true);
    setError('');
    setFinalAnswer('');
    
    const initialSteps: ReasoningStep[] = [
      { node: 'planner', status: 'running' },
      { node: 'retriever', status: 'running' },
      { node: 'responder', status: 'running' },
    ];
    setReasoningSteps(initialSteps);

    try {
      const response = await fetch('http://127.0.0.1:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      if (!response.body) throw new Error("Response body is empty.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let finalAnswerChunk = '';
      const streamReader = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n\n').filter(line => line.startsWith('data: '));
          for (const line of lines) {
            const jsonString = line.replace('data: ', '');
            if (!jsonString) continue;
            try {
              const eventData = JSON.parse(jsonString);
              if (eventData.type === 'answer') {
                finalAnswerChunk = eventData.content;
              }
            } catch (e) {
              console.error('Failed to parse event JSON:', jsonString);
            }
          }
        }
      };
      await streamReader();
      setFinalAnswer(finalAnswerChunk);
      setReasoningSteps(prev => prev.map(step => ({ ...step, status: 'finished' })));
    } catch (error: any) {
      console.error('API call failed:', error);
      setError('Failed to connect to the Cortex AI agent. Please ensure the backend is running.');
      setReasoningSteps([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadStatus({ inProgress: true, message: `Ingesting ${file.name}...`, isError: false });
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch('http://127.0.0.1:8000/ingestion/upload/pdf', {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || 'Upload failed');
      }
      setUploadStatus({ inProgress: false, message: result.message, isError: false });
      setTimeout(fetchKnowledgeSources, 2500);
    } catch (err: any) {
      setUploadStatus({ inProgress: false, message: `Error: ${err.message}`, isError: true });
    } finally {
      setTimeout(() => setUploadStatus({ inProgress: false, message: '', isError: false }), 7000);
    }
  };

  const handleLinkSubmit = async () => {
    const urlArray = links.split('\n').map(link => link.trim()).filter(Boolean);
    if (urlArray.length === 0) return;
    setUploadStatus({ inProgress: true, message: `Validating ${urlArray.length} link(s)...`, isError: false });
    try {
      const response = await fetch('http://127.0.0.1:8000/ingestion/links', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: urlArray }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || 'Link submission failed');
      }
      
      if (result.status === "processing_started_partially") {
          setUploadStatus({ inProgress: false, message: `${result.message} Failed links: ${result.failed_urls.join(', ')}`, isError: true });
      } else {
          setUploadStatus({ inProgress: false, message: result.message, isError: false });
      }
      setLinks('');
      setTimeout(fetchKnowledgeSources, 2500);
    } catch (err: any) {
      setUploadStatus({ inProgress: false, message: `Error: ${err.message}. Please ensure links are public and accessible.`, isError: true });
    } finally {
      setTimeout(() => setUploadStatus({ inProgress: false, message: '', isError: false }), 10000);
    }
  };

  const handleClearKnowledgeBase = async () => {
    setUploadStatus({ inProgress: true, message: 'Clearing all knowledge sources...', isError: false });
    try {
      const response = await fetch('http://127.0.0.1:8000/knowledge/clear', { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || 'Failed to clear');
      }
      setUploadStatus({ inProgress: false, message: result.message, isError: false });
      fetchKnowledgeSources();
    } catch (err: any) {
      setUploadStatus({ inProgress: false, message: `Error: ${err.message}`, isError: true });
    } finally {
      setTimeout(() => setUploadStatus({ inProgress: false, message: '', isError: false }), 5000);
    }
  };

  return (
    <main className="relative flex min-h-screen flex-col items-center bg-slate-900 text-slate-50 p-4 sm:p-8 md:p-12 overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />
      <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept="application/pdf" />

      <div className="relative z-10 w-full max-w-6xl space-y-8">
        <div className="text-center space-y-4 pt-8 animate-in fade-in slide-in-from-top duration-1000">
          <h1 className="text-7xl sm:text-8xl font-bold tracking-tighter text-slate-100">CORTEX</h1>
          <p className="text-slate-400 text-lg font-light tracking-wide max-w-2xl mx-auto">Your personal, context-aware RAG agent</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-1000">
          <Card className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 shadow-xl">
            <CardHeader><CardTitle className="flex items-center gap-3 text-lg font-semibold"><Upload className="h-5 w-5 text-slate-400" /> <span className="text-slate-200">Ingest Documents</span></CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-4">
              <Button variant="outline" onClick={() => fileInputRef.current?.click()} className="h-12 text-sm justify-center" disabled={uploadStatus.inProgress}><Upload className="mr-2 h-4 w-4" /> Upload PDF (Max 6MB)</Button>
              <Textarea value={links} onChange={(e) => setLinks(e.target.value)} placeholder="Or enter public web links, one per line..." className="bg-slate-800/80 border-slate-700/50 text-slate-100" rows={3}/>
              <Button onClick={handleLinkSubmit} className="h-12 text-sm" disabled={uploadStatus.inProgress || !links.trim()}><Link className="mr-2 h-4 w-4" /> Ingest Links</Button>
            </CardContent>
          </Card>
          <Card className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-lg font-semibold">
                <div className="flex items-center gap-3">
                  <BookOpen className="h-5 w-5 text-slate-400" />
                  <span className="text-slate-200">Knowledge Base</span>
                </div>
                <Button variant="ghost" size="sm" onClick={fetchKnowledgeSources} className="text-slate-400 hover:text-slate-100"> <RefreshCw className="h-4 w-4" /> </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {knowledgeSources.length > 0 ? (
                <div className="flex flex-col gap-4">
                  <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
                    {knowledgeSources.map((source, index) => (
                      <div key={index} className="px-3 py-1.5 border border-slate-700/50 rounded-full bg-slate-800/50"><span className="text-xs font-mono text-slate-400">{source}</span></div>
                    ))}
                  </div>
                  <Button variant="destructive" size="sm" onClick={handleClearKnowledgeBase} disabled={uploadStatus.inProgress}><XCircle className="mr-2 h-4 w-4" /> Clear Knowledge Base</Button>
                </div>
              ) : ( <p className="text-sm text-slate-500">The knowledge base is empty. Upload a PDF or ingest links to begin.</p> )}
            </CardContent>
          </Card>
        </div>
        {uploadStatus.message && (<div className={`mt-4 text-sm text-center p-3 rounded-lg ${uploadStatus.isError ? 'bg-red-900/50 text-red-300' : 'bg-green-900/50 text-green-300'}`}>{uploadStatus.message}</div>)}

        <Card className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 shadow-2xl animate-in fade-in slide-in-from-bottom duration-1000">
          <CardHeader><CardTitle className="flex items-center gap-3 text-lg font-semibold"><Search className="h-5 w-5 text-slate-400" /> <span className="text-slate-200">Ask a Question</span></CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-3">
              <Input type="text" value={question} onChange={(e) => setQuestion(e.target.value)} onKeyPress={handleKeyPress} className="h-14 text-base bg-slate-800/80 border-slate-700/50 text-slate-100" placeholder={knowledgeSources.length > 0 ? 'Ask about the ingested content...' : 'First, provide a knowledge source...'} disabled={isLoading || knowledgeSources.length === 0} />
              <Button onClick={handleSubmit} className="h-14 px-8 text-sm font-semibold" disabled={isLoading || !question}> {isLoading ? (<><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Processing</>) : (<>Execute <ArrowRight className="ml-2 h-5 w-5" /></>)}</Button>
            </div>
          </CardContent>
        </Card>
        
        {error && ( <Card className="bg-red-950/30 border-red-900/50"><CardContent className="p-5 flex items-center gap-4"><AlertTriangle className="h-6 w-6 text-red-400" /><div><p className="text-red-300 font-semibold">Connection Error</p><p className="text-red-400/80 text-sm">{error}</p></div></CardContent></Card> )}
        
        {(isLoading || finalAnswer) && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-2 space-y-3">
              <Card className="bg-slate-900/50 border-slate-700/50">
                <CardHeader><CardTitle className="flex items-center gap-3 text-lg"><Cpu className="h-4 w-4" /> Processing Pipeline</CardTitle></CardHeader>
                <CardContent className="p-4 space-y-2">
                  {reasoningSteps.map((step, index) => {
                    const config = nodeToConfig(step.node);
                    return (
                      <div key={index} className={`flex items-center gap-3 p-4 rounded-lg border transition-all duration-500 ${step.status === 'running' ? 'bg-slate-800/60 border-slate-600/50' : 'bg-slate-800/30 border-slate-700/30'}`}>
                        <div className={`p-2 rounded-md ${step.status === 'running' ? 'bg-slate-700' : 'bg-slate-800'}`}>
                          {step.status === 'finished' ? <CheckCircle className="h-5 w-5 text-slate-400" /> : <div className="animate-spin text-slate-400">{config.icon}</div>}
                        </div>
                        <p className="font-semibold text-slate-200 text-sm">{config.label}</p>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            </div>
            <div className="lg:col-span-3">
              <Card className="bg-slate-900/50 border-slate-700/50">
                <CardHeader><CardTitle className="flex items-center gap-3 text-lg"><Radio className="h-4 w-4" /> Response Output</CardTitle></CardHeader>
                <CardContent>
                  {isLoading && !finalAnswer ? (
                    <div className="flex items-center justify-center p-12 text-slate-500"><Loader2 className="mr-3 h-6 w-6 animate-spin" /> Waiting for response...</div>
                  ) : (
                    <p className="text-slate-300 leading-relaxed text-base p-4 bg-slate-800/30 rounded-lg">{finalAnswer}</p>
                  )}
                </CardContent>
              </Card>
            </div>
        </div>
        )}
      </div>
    </main>
  );
}

