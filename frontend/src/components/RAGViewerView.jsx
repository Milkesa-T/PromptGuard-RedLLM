import React, { useState, useEffect } from 'react';
import { Search, FileText, Lock, BookOpen, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';

export default function RAGViewerView() {
  const [documents, setDocuments] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [loadingDocs, setLoadingDocs] = useState(true);

  // Search State
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(3);
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchLatency, setSearchLatency] = useState(null);

  const fetchDocuments = async () => {
    try {
      setLoadingDocs(true);
      const res = await fetch('/api/rag/documents');
      if (res.ok) {
        const data = await res.json();
        const docs = data.documents || [];
        setDocuments(docs);
        setTotalChunks(data.total_chunks || 0);
      }
    } catch (err) {
      console.error('Failed to load RAG documents:', err);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleSearch = async (searchQuery = query) => {
    const q = searchQuery.trim();
    if (!q) return;

    try {
      setSearching(true);
      const startTime = performance.now();
      const res = await fetch('/api/rag/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, top_k: Number(topK) })
      });

      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
        setSearchLatency((performance.now() - startTime).toFixed(1));
      }
    } catch (err) {
      alert('RAG search failed: ' + err.message);
    } finally {
      setSearching(false);
    }
  };

  // Derive dynamic search suggestions based on the actual indexed documents
  const dynamicSuggestions = documents.map(doc =>
    doc.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ')
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f1f5f9' }}>RAG Knowledge Base & Vector Retrieval</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Inspect indexed corporate grounding documents and test raw cosine vector similarity search.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="badge badge-primary">{totalChunks} Chunks Indexed</span>
          <button className="btn btn-secondary" onClick={fetchDocuments} disabled={loadingDocs}>
            <RefreshCw size={14} className={loadingDocs ? 'spin-icon' : ''} />
            Refresh Docs
          </button>
        </div>
      </div>

      {/* Document List Cards */}
      <div>
        <h4 style={{ fontSize: '0.9rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: '1rem', fontWeight: 600 }}>
          Indexed Grounding Documents ({documents.length})
        </h4>

        {loadingDocs ? (
          <div className="card text-center text-muted" style={{ padding: '2rem' }}>Loading documents...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
            {documents.map((doc, idx) => {
              const isInternal = doc.toLowerCase().includes('internal') || doc.toLowerCase().includes('admin');
              const cleanTitle = doc.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
              return (
                <div key={idx} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', borderLeft: isInternal ? '3px solid #ef4444' : '3px solid #38bdf8' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {isInternal ? <Lock size={18} color="#f87171" /> : <FileText size={18} color="#38bdf8" />}
                        <strong style={{ fontSize: '0.95rem' }}>{doc}</strong>
                      </div>
                      <span className={`badge ${isInternal ? 'badge-danger' : 'badge-primary'}`} style={{ fontSize: '0.7rem' }}>
                        {isInternal ? 'Confidential' : 'Knowledge'}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Retrieved source document indexed into embedding space for agent grounding.
                    </p>
                  </div>
                  <div style={{ marginTop: '1.25rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <CheckCircle2 size={13} /> Active in Index
                    </span>
                    <button
                      className="btn btn-xs btn-secondary"
                      onClick={() => {
                        setQuery(cleanTitle);
                        handleSearch(cleanTitle);
                      }}
                    >
                      <Search size={12} /> Test Search
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Semantic Vector Search Explorer */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3>Semantic Vector Search Explorer</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              Query the embedding index directly via <code>POST /api/rag/search</code>
            </p>
          </div>
        </div>

        {/* Dynamic query badges derived directly from active documents */}
        {dynamicSuggestions.length > 0 && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Dynamic Suggestions:</span>
            {dynamicSuggestions.map((suggestion, idx) => (
              <button
                key={idx}
                className="badge badge-secondary"
                style={{ cursor: 'pointer', border: '1px solid var(--border-color)', textTransform: 'capitalize' }}
                onClick={() => {
                  setQuery(suggestion);
                  handleSearch(suggestion);
                }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <input
            type="text"
            className="form-control"
            placeholder="Enter natural language query to retrieve matching chunks..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <select
            className="form-control"
            style={{ width: '120px', flexShrink: 0 }}
            value={topK}
            onChange={(e) => setTopK(e.target.value)}
          >
            <option value="2">Top 2</option>
            <option value="3">Top 3</option>
            <option value="5">Top 5</option>
          </select>
          <button className="btn btn-primary" onClick={() => handleSearch()} disabled={searching || !query.trim()} style={{ flexShrink: 0 }}>
            <Search size={15} />
            {searching ? 'Searching...' : 'Search RAG'}
          </button>
        </div>

        {/* Search Results Display */}
        {searchResults && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', paddingBottom: '0.5rem', borderBottom: '1px solid var(--border-color)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Matched <strong>{searchResults.matches_found}</strong> chunks for "<em>{searchResults.query}</em>"
              </span>
              <span className="badge badge-primary">{searchLatency}ms latency</span>
            </div>

            {searchResults.chunks && searchResults.chunks.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {searchResults.chunks.map((chunk, idx) => (
                  <div key={idx} className="card" style={{ background: '#090e1a', padding: '1rem', borderLeft: '3px solid var(--primary)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="badge badge-primary" style={{ fontSize: '0.7rem' }}>Chunk #{chunk.chunk_id || idx + 1}</span>
                        <strong style={{ fontSize: '0.85rem' }}>{chunk.doc_name || chunk.source || 'Knowledge'}</strong>
                      </div>
                      <span className="badge badge-secondary" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                        Score: {typeof chunk.score === 'number' ? chunk.score.toFixed(3) : chunk.score || 'Matched'}
                      </span>
                    </div>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: '#cbd5e1', fontFamily: 'var(--font-main)', lineHeight: 1.6 }}>
                      {chunk.text || chunk.content}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <div className="card text-center text-muted" style={{ padding: '2rem' }}>
                No relevant chunks found.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
