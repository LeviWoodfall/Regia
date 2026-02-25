import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Trash2, Brain, BookOpen, ChevronDown, ChevronUp, X } from 'lucide-react';
import { chatWithReggie, getAgentStatus, clearChatHistory, getMemories, deleteMemory } from '../lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  suggestions?: string[];
  learned?: any[];
  memory_count?: number;
  knowledge_count?: number;
}

export default function ReggiePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentAvailable, setAgentAvailable] = useState<boolean | null>(null);
  const [agentModel, setAgentModel] = useState('');
  const [memoryStats, setMemoryStats] = useState<any>(null);
  const [knowledgeStats, setKnowledgeStats] = useState<any>(null);
  const [showMemoryPanel, setShowMemoryPanel] = useState(false);
  const [memories, setMemories] = useState<any[]>([]);
  const messagesEnd = useRef<HTMLDivElement>(null);

  const loadStatus = () => {
    getAgentStatus()
      .then(r => {
        setAgentAvailable(r.data.available);
        setAgentModel(r.data.model || '');
        setMemoryStats(r.data.memory_stats || null);
        setKnowledgeStats(r.data.knowledge_stats || null);
      })
      .catch(() => setAgentAvailable(false));
  };

  useEffect(() => { loadStatus(); }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg || loading) return;

    setInput('');
    const userMsg: Message = { role: 'user', content: msg };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const resp = await chatWithReggie({
        message: msg,
        session_id: sessionId,
      });
      const data = resp.data;
      if (data.session_id) setSessionId(data.session_id);

      const assistantMsg: Message = {
        role: 'assistant',
        content: data.message,
        sources: data.sources,
        suggestions: data.suggestions,
        learned: data.learned,
        memory_count: data.memory_count,
        knowledge_count: data.knowledge_count,
      };
      setMessages(prev => [...prev, assistantMsg]);
      // Refresh stats after learning
      if (data.learned?.length) loadStatus();
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "I'm having trouble connecting right now. Please make sure the Regia backend and Ollama are running.",
      }]);
    }
    setLoading(false);
  };

  const handleClear = async () => {
    if (sessionId) {
      try { await clearChatHistory(sessionId); } catch { /* ignore */ }
    }
    setMessages([]);
    setSessionId(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sunset-400 to-warm-600 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-warm-900">Reggie</h2>
            <p className="text-xs text-sand-500">
              {agentAvailable === null
                ? 'Checking availability…'
                : agentAvailable
                  ? `Online · ${agentModel}`
                  : 'Offline — Rule-based mode'
              }
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {memoryStats && (memoryStats.total > 0 || (knowledgeStats && knowledgeStats.total > 0)) && (
            <button
              onClick={async () => {
                setShowMemoryPanel(!showMemoryPanel);
                if (!showMemoryPanel) {
                  try {
                    const r = await getMemories();
                    setMemories(r.data.memories || []);
                  } catch { /* ignore */ }
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-sunset-600 hover:text-sunset-700 bg-sunset-50 hover:bg-sunset-100 rounded-lg transition-colors"
              title="Reggie's memory & knowledge"
            >
              <Brain className="w-3.5 h-3.5" />
              {memoryStats.total > 0 && <span>{memoryStats.total} memories</span>}
              {knowledgeStats?.total > 0 && <span className="text-sand-400">·</span>}
              {knowledgeStats?.total > 0 && <span>{knowledgeStats.total} facts</span>}
            </button>
          )}
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-sand-500 hover:text-warm-700 hover:bg-sand-100 rounded-lg transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" /> Clear
            </button>
          )}
        </div>
      </div>

      {/* Memory Panel */}
      {showMemoryPanel && (
        <div className="mb-3 bg-sunset-50 border border-sunset-200 rounded-xl p-4 max-h-60 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-semibold text-warm-900 flex items-center gap-1.5">
              <Brain className="w-4 h-4 text-sunset-500" /> Reggie's Memory
            </h4>
            <button onClick={() => setShowMemoryPanel(false)} className="text-sand-400 hover:text-warm-600">
              <X className="w-4 h-4" />
            </button>
          </div>
          {memories.length === 0 ? (
            <p className="text-xs text-sand-500">No memories yet. Chat with Reggie to help him learn!</p>
          ) : (
            <div className="space-y-1.5">
              {memories.map((m: any) => (
                <div key={m.id} className="flex items-start justify-between gap-2 text-xs">
                  <div className="flex-1 min-w-0">
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium mr-1.5 ${
                      m.memory_type === 'preference' ? 'bg-blue-100 text-blue-700' :
                      m.memory_type === 'instruction' ? 'bg-purple-100 text-purple-700' :
                      m.memory_type === 'correction' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-sand-200 text-sand-600'
                    }`}>{m.memory_type}</span>
                    <span className="text-warm-700">{m.content}</span>
                  </div>
                  <button
                    onClick={async () => {
                      await deleteMemory(m.id);
                      setMemories(prev => prev.filter(x => x.id !== m.id));
                      loadStatus();
                    }}
                    className="text-sand-400 hover:text-red-500 shrink-0 p-0.5"
                    title="Delete memory"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto rounded-2xl bg-white border border-sand-200 shadow-sm">
        <div className="p-5 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-16 text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-sunset-200 to-warm-300 flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-sunset-600" />
              </div>
              <h3 className="text-lg font-semibold text-warm-900">Hey, I'm Reggie!</h3>
              <p className="text-sm text-sand-500 mt-1 max-w-md">
                I can help you find documents, search through emails, and answer questions about your ingested data.
                I learn from our conversations and from your documents — the more we chat, the smarter I get!
              </p>
              <div className="flex flex-wrap gap-2 mt-6 justify-center">
                {[
                  'Show me recent invoices',
                  'Find tax documents from 2024',
                  'What documents came in today?',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleSend(suggestion)}
                    className="px-3 py-2 bg-sand-100 hover:bg-sunset-100 text-sand-600 hover:text-sunset-700 rounded-xl text-xs font-medium transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-sunset-400 to-warm-500 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}
                <div className={`max-w-[70%] ${
                  msg.role === 'user'
                    ? 'bg-sunset-500 text-white rounded-2xl rounded-br-md px-4 py-2.5'
                    : 'bg-sand-50 text-warm-900 rounded-2xl rounded-bl-md px-4 py-2.5'
                }`}>
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-sand-200">
                      <p className="text-[10px] font-medium text-sand-500 mb-1">Sources:</p>
                      {msg.sources.slice(0, 3).map((s: any, i: number) => (
                        <p key={i} className="text-[11px] text-sand-600">
                          • {s.title} ({s.type})
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Learning indicator */}
                  {msg.learned && msg.learned.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-sunset-200/50">
                      <p className="text-[10px] font-medium text-sunset-500 flex items-center gap-1">
                        <Brain className="w-3 h-3" /> Learned {msg.learned.length} new thing{msg.learned.length > 1 ? 's' : ''}
                      </p>
                    </div>
                  )}

                  {/* Context indicator */}
                  {msg.role === 'assistant' && (msg.memory_count || 0) + (msg.knowledge_count || 0) > 0 && (
                    <div className="mt-1">
                      <p className="text-[10px] text-sand-400 flex items-center gap-1">
                        <BookOpen className="w-3 h-3" />
                        Used {msg.memory_count || 0} memories, {msg.knowledge_count || 0} knowledge facts
                      </p>
                    </div>
                  )}

                  {/* Suggestions */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {msg.suggestions.map((s: string, i: number) => (
                        <button
                          key={i}
                          onClick={() => handleSend(s)}
                          className="px-2 py-1 bg-white/80 hover:bg-white text-warm-700 rounded-lg text-[11px] font-medium transition-colors border border-sand-200"
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-lg bg-warm-200 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-4 h-4 text-warm-600" />
                  </div>
                )}
              </div>
            ))
          )}
          {loading && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-sunset-400 to-warm-500 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-sand-50 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-sand-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-sand-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-sand-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEnd} />
        </div>
      </div>

      {/* Input Area */}
      <div className="mt-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Reggie anything about your documents…"
            rows={1}
            className="flex-1 px-4 py-3 bg-white border border-sand-200 rounded-2xl text-sm
                       text-warm-900 placeholder-sand-400 shadow-sm resize-none
                       focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400
                       transition-all duration-200"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="px-4 py-3 bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-2xl
                       shadow-sm hover:shadow-md transition-all duration-200
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
