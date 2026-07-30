import { useState } from 'react'
import { Bot, FileJson, Mail, Table } from 'lucide-react'
import { extractions } from '../services/api'

export default function Extractions() {
  const [content, setContent] = useState('')
  const [schema, setSchema] = useState('')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'extract' | 'classify' | 'contacts' | 'table'>('extract')
  const [categories, setCategories] = useState('product, article, job listing, company page')

  const handleExtract = async () => {
    setLoading(true)
    setResult(null)
    try {
      let res
      switch (mode) {
        case 'extract':
          res = await extractions.extract({
            content,
            schema: schema ? JSON.parse(schema) : undefined,
          })
          break
        case 'classify':
          res = await extractions.classify({
            content,
            categories: categories.split(',').map(c => c.trim()),
          })
          break
        case 'contacts':
          res = await extractions.extractContacts(content)
          break
        case 'table':
          res = await extractions.extractTable(content)
          break
      }
      setResult(res)
    } catch (err: any) {
      setResult({ error: err.message })
    } finally {
      setLoading(false)
    }
  }

  const copyResult = () => {
    if (result) {
      navigator.clipboard.writeText(JSON.stringify(result, null, 2))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">AI Extraction</h1>
        <p className="text-gray-500 mt-1">Extract structured data using LLMs</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card space-y-4">
          <div className="flex gap-2">
            {(['extract', 'classify', 'contacts', 'table'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  mode === m
                    ? 'bg-brand-600/20 text-brand-400 border border-brand-600/30'
                    : 'text-gray-400 hover:text-gray-200 bg-gray-800'
                }`}
              >
                {m === 'extract' && <><FileJson className="w-4 h-4 inline mr-1" /> Extract</>}
                {m === 'classify' && <><Bot className="w-4 h-4 inline mr-1" /> Classify</>}
                {m === 'contacts' && <><Mail className="w-4 h-4 inline mr-1" /> Contacts</>}
                {m === 'table' && <><Table className="w-4 h-4 inline mr-1" /> Table</>}
              </button>
            ))}
          </div>

          {mode === 'classify' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Categories (comma-separated)</label>
              <input type="text" value={categories} onChange={e => setCategories(e.target.value)} className="input" />
            </div>
          )}

          {mode === 'extract' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">JSON Schema (optional)</label>
              <textarea
                value={schema}
                onChange={e => setSchema(e.target.value)}
                className="input font-mono text-xs"
                rows={4}
                placeholder='{"type":"object","properties":{"title":{"type":"string"}}}'
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Web Content</label>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              className="input font-mono text-xs"
              rows={12}
              placeholder="Paste HTML or text content here..."
            />
          </div>

          <button
            onClick={handleExtract}
            disabled={loading || !content}
            className="btn-primary w-full"
          >
            {loading ? 'Processing...' : 'Run Extraction'}
          </button>
        </div>

        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Result</h3>
            {result && (
              <button onClick={copyResult} className="btn-secondary text-xs py-1 px-2">
                Copy
              </button>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
            </div>
          ) : result ? (
            <div className="space-y-4">
              {result.error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
                  {result.error}
                </div>
              )}
              {result.data && (
                <div>
                  <pre className="text-xs text-gray-300 bg-gray-950 rounded-lg p-4 overflow-auto max-h-96 font-mono">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </div>
              )}
              <div className="flex gap-4 text-xs text-gray-500">
                {result.confidence_score && (
                  <span>Confidence: {(result.confidence_score * 100).toFixed(0)}%</span>
                )}
                {result.tokens_used > 0 && <span>Tokens: {result.tokens_used}</span>}
                {result.processing_time_ms && <span>Time: {result.processing_time_ms}ms</span>}
                {result.model_used && <span>Model: {result.model_used}</span>}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
              <Bot className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm">Run an extraction to see results</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
