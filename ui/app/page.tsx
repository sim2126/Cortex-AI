"use client";

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Network, Search, BrainCircuit, CheckCircle, AlertTriangle, Database, ArrowRight, Activity, Cpu, Radio } from "lucide-react";

type ReasoningStep = {
  node: string;
  status: 'running' | 'finished' | 'error';
  timestamp?: number;
};

export default function Home() {
  const [question, setQuestion] = useState<string>('');
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([]);
  const [finalAnswer, setFinalAnswer] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [ripples, setRipples] = useState<Array<{id: number, x: number, y: number}>>([]);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rippleIdRef = useRef(0);

  // Grid animation
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
      if (!ctx) return;
      ctx.fillStyle = 'rgba(15, 23, 42, 1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = 'rgba(51, 65, 85, 0.3)';
      ctx.lineWidth = 1;

      // Vertical lines
      for (let x = (offset % gridSize) - gridSize; x < canvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }

      // Horizontal lines
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
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const createRipple = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const id = rippleIdRef.current++;
    
    setRipples(prev => [...prev, { id, x, y }]);
    setTimeout(() => {
      setRipples(prev => prev.filter(r => r.id !== id));
    }, 600);
  };

  const nodeToConfig = (node: string) => {
    const configs = {
      router: { 
        icon: <Network className="h-5 w-5" />, 
        color: 'from-slate-400 to-slate-500',
        label: 'Query Router',
        description: 'Semantic analysis'
      },
      vectorstore: { 
        icon: <Database className="h-5 w-5" />, 
        color: 'from-slate-400 to-slate-500',
        label: 'Vector Store',
        description: 'Embedding retrieval'
      },
      graph: { 
        icon: <Activity className="h-5 w-5" />, 
        color: 'from-slate-400 to-slate-500',
        label: 'Knowledge Graph',
        description: 'Relation traversal'
      },
      responder: { 
        icon: <BrainCircuit className="h-5 w-5" />, 
        color: 'from-slate-400 to-slate-500',
        label: 'Response Engine',
        description: 'Output synthesis'
      },
    };
    return configs[node as keyof typeof configs] || { 
      icon: <Cpu className="h-5 w-5" />, 
      color: 'from-slate-400 to-slate-500',
      label: node,
      description: 'Processing'
    };
  };

  const handleSubmit = async () => {
    if (!question || isLoading) return;

    setIsLoading(true);
    setError('');
    setFinalAnswer('');
    setReasoningSteps([]);

    try {
      const response = await fetch('http://127.0.0.1:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });

      if (!response.body) throw new Error("Response body is empty.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

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
            
            if (eventData.type === 'thought') {
              const thought = eventData.content;
              
              setReasoningSteps(prev => {
                let newSteps = [...prev];
                if (newSteps.length > 0 && newSteps[newSteps.length - 1].status === 'running') {
                  newSteps[newSteps.length - 1] = { ...newSteps[newSteps.length - 1], status: 'finished' };
                }

                if (thought.toLowerCase().includes("plan")) {
                  newSteps.push({ node: 'router', status: 'running', timestamp: Date.now() });
                } else if (thought.toLowerCase().includes("executing step")) {
                  newSteps.push({ node: 'graph', status: 'running', timestamp: Date.now() });
                } else if (thought.toLowerCase().includes("synthesizing")) {
                  newSteps.push({ node: 'responder', status: 'running', timestamp: Date.now() });
                }
                return newSteps;
              });

            } else if (eventData.type === 'answer') {
              setFinalAnswer(eventData.content);
              setReasoningSteps(prev => prev.map(step => 
                step.status === 'running' ? { ...step, status: 'finished' } : step
              ));
            }

          } catch (e) {
            console.error('Failed to parse event JSON:', jsonString);
          }
        }
      }
    } catch (error: any) {
      console.error('API call failed:', error);
      setError('Failed to connect to the Cortex AI agent. Please ensure the backend is running.');
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

  return (
    <main className="relative flex min-h-screen flex-col items-center bg-slate-900 text-slate-50 p-4 sm:p-8 md:p-12 overflow-hidden">
      <canvas 
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none"
      />

      <div 
        className="absolute w-[600px] h-[600px] pointer-events-none transition-all duration-700 ease-out opacity-20"
        style={{
          left: mousePos.x - 300,
          top: mousePos.y - 300,
          background: 'radial-gradient(circle, rgba(148, 163, 184, 0.15) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-6xl space-y-12">
        <div className="text-center space-y-8 pt-12 animate-in fade-in slide-in-from-top duration-1000">
          <div className="inline-flex items-center gap-3 px-4 py-2 border border-slate-700/50 rounded-full bg-slate-900/50 backdrop-blur-sm">
            <div className="w-2 h-2 bg-slate-400 rounded-full animate-pulse" />
            <span className="text-xs font-mono text-slate-400 tracking-wider uppercase">System Active</span>
          </div>
          
          <div className="space-y-4">
            <h1 className="text-7xl sm:text-8xl font-bold tracking-tighter text-slate-100">
              CORTEX
            </h1>
            <p className="text-slate-400 text-lg font-light tracking-wide max-w-2xl mx-auto">
              Advanced agentic intelligence system with neural retrieval augmentation
            </p>
          </div>
        </div>
        
        <Card className="relative overflow-hidden bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 shadow-2xl animate-in fade-in slide-in-from-bottom duration-1000">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-grow group">
                <div className="absolute inset-0 bg-slate-700/20 rounded-lg blur-xl opacity-0 group-focus-within:opacity-100 transition-all duration-500" />
                <div className="relative flex items-center">
                  <Search className="absolute left-4 h-5 w-5 text-slate-500 group-focus-within:text-slate-400 transition-colors z-10" />
                  <Input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="relative pl-12 pr-24 bg-slate-800/80 backdrop-blur-xl border border-slate-700/50 h-14 text-base font-medium text-white placeholder:text-slate-500 focus-visible:ring-1 focus-visible:ring-slate-600 focus-visible:ring-offset-0 focus-visible:border-slate-600 transition-all duration-300 rounded-lg"
                    placeholder="Enter query"
                    disabled={isLoading}
                  />
                  {question && !isLoading && (
                    <div className="absolute right-4 flex items-center gap-2 text-xs text-slate-500 font-mono">
                      <kbd className="px-2 py-1 bg-slate-700/80 border border-slate-600/50 rounded text-xs">↵</kbd>
                    </div>
                  )}
                </div>
              </div>
              <Button
                onClick={(e) => {
                  createRipple(e);
                  handleSubmit();
                }}
                className="relative overflow-hidden h-14 px-8 text-sm font-semibold bg-slate-100 hover:bg-white text-slate-950 transition-all duration-300 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed rounded-lg border border-slate-200/20"
                disabled={isLoading}
              >
                {ripples.map(ripple => (
                  <span
                    key={ripple.id}
                    className="absolute bg-slate-950/20 rounded-full animate-ping"
                    style={{
                      left: ripple.x,
                      top: ripple.y,
                      width: 10,
                      height: 10,
                      transform: 'translate(-50%, -50%)'
                    }}
                  />
                ))}
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" /> 
                    Processing
                  </>
                ) : (
                  <>
                    Execute
                    <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Card className="bg-red-950/30 backdrop-blur-xl border border-red-900/50 shadow-xl animate-in fade-in slide-in-from-top duration-500">
            <CardContent className="p-5 flex items-center gap-4">
              <AlertTriangle className="h-6 w-6 text-red-400 flex-shrink-0" />
              <div>
                <p className="text-red-300 font-semibold">Connection Error</p>
                <p className="text-red-400/80 text-sm">{error}</p>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {(isLoading || reasoningSteps.length > 0) && (
            <div className="lg:col-span-2 space-y-3 animate-in fade-in slide-in-from-left duration-1000">
              <Card className="overflow-hidden bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 shadow-xl">
                <CardHeader className="border-b border-slate-700/50 bg-slate-800/50">
                  <CardTitle className="flex items-center gap-3 text-lg font-semibold">
                    <div className="p-1.5 bg-slate-700/80 rounded-md">
                      <Cpu className="h-4 w-4 text-slate-400" />
                    </div>
                    <span className="text-slate-200">Processing Pipeline</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 space-y-2">
                  {reasoningSteps.map((step, index) => {
                    const config = nodeToConfig(step.node);
                    const isActive = step.status === 'running';
                    
                    return (
                      <div
                        key={index}
                        className={`relative group transition-all duration-500 ${
                          isActive ? 'scale-[1.02]' : ''
                        }`}
                      >
                        <div className={`flex items-center gap-3 p-4 rounded-lg border backdrop-blur-sm transition-all duration-500 ${
                          isActive
                            ? 'bg-slate-800/60 border-slate-600/50 shadow-lg'
                            : 'bg-slate-800/30 border-slate-700/30 hover:bg-slate-800/50'
                        }`}>
                          <div className={`p-2 rounded-md ${isActive ? 'bg-slate-700' : 'bg-slate-800'} transition-colors duration-500`}>
                            {step.status === 'finished' ? (
                              <CheckCircle className="h-5 w-5 text-slate-400" />
                            ) : (
                              <div className="animate-spin text-slate-400">
                                {config.icon}
                              </div>
                            )}
                          </div>
                          
                          <div className="flex-grow min-w-0">
                            <p className="font-semibold text-slate-200 text-sm">{config.label}</p>
                            <p className="text-xs text-slate-500 truncate">{config.description}</p>
                          </div>
                          
                          {isActive ? (
                            <div className="flex gap-0.5">
                              {[0, 1, 2].map((i) => (
                                <div 
                                  key={i}
                                  className="w-1 h-6 bg-slate-600 rounded-full animate-pulse"
                                  style={{ animationDelay: `${i * 0.15}s` }}
                                />
                              ))}
                            </div>
                          ) : (
                            <div className="px-2 py-1 bg-slate-800 rounded text-xs font-mono text-slate-400">
                              OK
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            </div>
          )}

          {finalAnswer && (
            <div className="lg:col-span-3 space-y-3 animate-in fade-in slide-in-from-right duration-1000">
              <Card className="overflow-hidden bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 shadow-xl">
                <CardHeader className="border-b border-slate-700/50 bg-slate-800/50">
                  <CardTitle className="flex items-center justify-between text-lg font-semibold">
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 bg-slate-700/80 rounded-md">
                        <Radio className="h-4 w-4 text-slate-400" />
                      </div>
                      <span className="text-slate-200">Response Output</span>
                    </div>
                    <div className="flex items-center gap-2 px-2 py-1 bg-slate-800 rounded-full">
                      <div className="w-1.5 h-1.5 bg-slate-400 rounded-full" />
                      <span className="text-xs font-mono text-slate-400">COMPLETE</span>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="relative">
                    <div className="p-6 rounded-lg bg-slate-800/30 border border-slate-700/50">
                      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-700/50">
                        <div className="flex gap-1.5">
                          <div className="w-3 h-3 rounded-full bg-slate-700" />
                          <div className="w-3 h-3 rounded-full bg-slate-700" />
                          <div className="w-3 h-3 rounded-full bg-slate-600" />
                        </div>
                        <div className="text-xs font-mono text-slate-600">cortex://output</div>
                      </div>
                      
                      <div className="prose prose-invert max-w-none">
                        <p className="text-slate-300 leading-relaxed text-base">
                          {finalAnswer}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {!isLoading && reasoningSteps.length === 0 && !finalAnswer && (
          <div className="text-center py-32 space-y-6 animate-in fade-in duration-1500">
            <div className="relative inline-block">
              <BrainCircuit className="h-20 w-20 text-slate-700" />
            </div>
            
            <div className="space-y-3">
              <h3 className="text-2xl font-semibold text-slate-300">
                System Initialized
              </h3>
              <p className="text-slate-500 text-sm max-w-md mx-auto">
                Awaiting input query for cognitive processing
              </p>
              
              <div className="flex items-center justify-center gap-4 pt-4">
                <div className="px-3 py-1.5 border border-slate-700/50 rounded-full backdrop-blur-sm">
                  <span className="text-xs font-mono text-slate-500">RAG</span>
                </div>
                <div className="px-3 py-1.5 border border-slate-700/50 rounded-full backdrop-blur-sm">
                  <span className="text-xs font-mono text-slate-500">Multi-Agent</span>
                </div>
                <div className="px-3 py-1.5 border border-slate-700/50 rounded-full backdrop-blur-sm">
                  <span className="text-xs font-mono text-slate-500">Neural</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

