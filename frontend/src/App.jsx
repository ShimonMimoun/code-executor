import { useState, useEffect, useCallback, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { executeCodeSync, listExecutions, getExecution, getHealth } from './api';
import './index.css';

const LANGUAGES = {
    python: {
        display: 'Python',
        versions: ['3.9', '3.10', '3.11', '3.12', '3.13'],
        defaultVersion: '3.12',
        monacoLang: 'python',
        depsPlaceholder: 'requests, numpy, pandas',
        defaultCode: `# Python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        print(a, end=' ')
        a, b = b, a + b
    print()

fibonacci(20)
`,
    },
    javascript: {
        display: 'Node.js',
        versions: ['18', '19', '20', '21', '22', '23', '24'],
        defaultVersion: '22',
        monacoLang: 'javascript',
        depsPlaceholder: 'lodash, axios, chalk',
        defaultCode: `// Node.js
function fibonacci(n) {
  let a = 0, b = 1;
  const result = [];
  for (let i = 0; i < n; i++) {
    result.push(a);
    [a, b] = [b, a + b];
  }
  console.log(result.join(' '));
}

fibonacci(20);
`,
    },
    go: {
        display: 'Go',
        versions: ['1.20', '1.21', '1.22', '1.23'],
        defaultVersion: '1.22',
        monacoLang: 'go',
        depsPlaceholder: 'github.com/google/uuid',
        defaultCode: `// Go
package main

import "fmt"

func fibonacci(n int) {
    a, b := 0, 1
    for i := 0; i < n; i++ {
        fmt.Printf("%d ", a)
        a, b = b, a+b
    }
    fmt.Println()
}

func main() {
    fibonacci(20)
}
`,
    },
    bash: {
        display: 'Bash',
        versions: ['5'],
        defaultVersion: '5',
        monacoLang: 'shell',
        depsPlaceholder: null,
        defaultCode: `#!/bin/bash
echo "System info:"
echo "  User: $(whoami)"
echo "  Shell: $SHELL"
echo "  Date: $(date)"
echo ""
echo "Fibonacci sequence:"
a=0; b=1
for i in $(seq 1 20); do
  printf "%d " $a
  temp=$((a + b))
  a=$b
  b=$temp
done
echo ""
`,
    },
    java: {
        display: 'Java',
        versions: ['17', '21', '22', '23'],
        defaultVersion: '21',
        monacoLang: 'java',
        depsPlaceholder: 'com.google.code.gson:gson:2.10.1',
        defaultCode: `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");

        // Fibonacci
        int a = 0, b = 1;
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 20; i++) {
            sb.append(a).append(" ");
            int temp = a + b;
            a = b;
            b = temp;
        }
        System.out.println(sb.toString().trim());
    }
}
`,
    },
    csharp: {
        display: 'C#',
        versions: ['8', '9'],
        defaultVersion: '8',
        monacoLang: 'csharp',
        depsPlaceholder: 'Newtonsoft.Json',
        defaultCode: `using System;
using System.Text;

// Fibonacci
int a = 0, b = 1;
var sb = new StringBuilder();
for (int i = 0; i < 20; i++)
{
    sb.Append(a).Append(" ");
    int temp = a + b;
    a = b;
    b = temp;
}
Console.WriteLine("Hello from C#!");
Console.WriteLine(sb.ToString().Trim());
`,
    },
    html: {
        display: 'HTML/CSS/JS',
        versions: ['5'],
        defaultVersion: '5',
        monacoLang: 'html',
        depsPlaceholder: null,
        outputType: 'html',
        defaultCode: `<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: sans-serif; background: #1a1a2e; color: #eee; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .card { background: #16213e; padding: 2rem; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); text-align: center; }
    h1 { background: linear-gradient(135deg, #e94560, #0f3460); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Hello World!</h1>
    <p id="time"></p>
  </div>
  <script>document.getElementById("time").textContent = new Date().toLocaleString();</script>
</body>
</html>`,
    },
    react: {
        display: 'React',
        versions: ['18', '19'],
        defaultVersion: '19',
        monacoLang: 'javascript', // Monaco uses mostly JS/JSX coloring here
        depsPlaceholder: null,
        outputType: 'html',
        defaultCode: `function App() {
  const [count, setCount] = React.useState(0);
  return (
    <div style={{fontFamily: "sans-serif", background: "#1a1a2e", color: "#eee", display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", margin: 0}}>
      <div style={{background: "#16213e", padding: "2rem", borderRadius: "12px", boxShadow: "0 8px 32px rgba(0,0,0,0.3)", textAlign: "center"}}>
        <h1 style={{background: "linear-gradient(135deg, #e94560, #0f3460)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"}}>React Counter</h1>
        <p style={{fontSize: "3rem", margin: "1rem 0"}}>{count}</p>
        <button onClick={() => setCount(c => c + 1)} style={{padding: "0.5rem 2rem", fontSize: "1rem", borderRadius: "8px", border: "none", background: "#e94560", color: "white", cursor: "pointer"}}>Click me!</button>
      </div>
    </div>
  );
}`,
    },
};

function App() {
    const [language, setLanguage] = useState('python');
    const [version, setVersion] = useState(LANGUAGES.python.defaultVersion);
    const [code, setCode] = useState(LANGUAGES.python.defaultCode);
    const [depsInput, setDepsInput] = useState('');
    const [output, setOutput] = useState(null);
    const [activeTab, setActiveTab] = useState('output');
    const [isRunning, setIsRunning] = useState(false);
    const [health, setHealth] = useState(null);
    const [history, setHistory] = useState([]);
    const [error, setError] = useState(null);
    const editorRef = useRef(null);

    // Health check
    useEffect(() => {
        const check = async () => setHealth(await getHealth());
        check();
        const interval = setInterval(check, 15000);
        return () => clearInterval(interval);
    }, []);

    // Load history
    useEffect(() => { listExecutions(10).then(setHistory).catch(() => { }); }, []);

    const handleLanguageChange = useCallback((e) => {
        const lang = e.target.value;
        const cfg = LANGUAGES[lang];
        setLanguage(lang);
        setVersion(cfg.defaultVersion);
        setCode(cfg.defaultCode);
        setDepsInput('');
    }, []);

    const handleRun = useCallback(async () => {
        setIsRunning(true);
        setError(null);
        setOutput(null);
        setActiveTab('output');

        // Parse dependencies
        const deps = depsInput.trim()
            ? depsInput.split(',').map(d => d.trim()).filter(Boolean)
            : undefined;

        try {
            const result = await executeCodeSync({
                code,
                language,
                version,
                dependencies: deps,
                timeout: 60,
            });
            setOutput(result);
            const hist = await listExecutions(10);
            setHistory(hist);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsRunning(false);
        }
    }, [code, language, version, depsInput]);

    const handleClear = useCallback(() => { setOutput(null); setError(null); }, []);

    const handleHistoryClick = useCallback(async (executionId) => {
        try {
            const result = await getExecution(executionId);
            setOutput(result);
            setActiveTab('output');
        } catch { /* ignore */ }
    }, []);

    const handleKeyDown = useCallback((e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); handleRun(); }
    }, [handleRun]);

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);

    const langConfig = LANGUAGES[language];
    const isConnected = health?.status === 'healthy';

    return (
        <div className="app-layout">
            {/* Header */}
            <header className="app-header">
                <div className="header-brand">
                    <div className="header-logo">⚡</div>
                    <div>
                        <div className="header-title">Code Executor</div>
                        <div className="header-subtitle">AI Agent Sandbox Platform</div>
                    </div>
                </div>
                <div className="header-status">
                    <div className={`status-badge ${isConnected ? '' : 'disconnected'}`}>
                        <span className="status-dot" />
                        {isConnected ? 'Connected' : 'Disconnected'}
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <div className="main-content">
                {/* Left: Code Editor */}
                <div className="editor-panel">
                    <div className="panel-header">
                        <span className="panel-title">Editor</span>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            {/* Language selector */}
                            <div className="language-selector">
                                <select value={language} onChange={handleLanguageChange} id="language-select">
                                    {Object.entries(LANGUAGES).map(([key, cfg]) => (
                                        <option key={key} value={key}>{cfg.display}</option>
                                    ))}
                                </select>
                            </div>
                            {/* Version selector */}
                            <div className="language-selector">
                                <select
                                    value={version}
                                    onChange={e => setVersion(e.target.value)}
                                    id="version-select"
                                >
                                    {langConfig.versions.map(v => (
                                        <option key={v} value={v}>v{v}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="editor-container">
                        <Editor
                            height="100%"
                            language={langConfig.monacoLang}
                            value={code}
                            onChange={(v) => setCode(v || '')}
                            theme="vs-dark"
                            options={{
                                minimap: { enabled: false },
                                fontSize: 14,
                                fontFamily: "'JetBrains Mono', monospace",
                                lineNumbers: 'on',
                                scrollBeyondLastLine: false,
                                automaticLayout: true,
                                padding: { top: 16, bottom: 16 },
                                renderLineHighlight: 'gutter',
                                bracketPairColorization: { enabled: true },
                                guides: { bracketPairs: true },
                                smoothScrolling: true,
                                cursorSmoothCaretAnimation: 'on',
                                tabSize: 2,
                            }}
                        />
                    </div>

                    {/* Dependencies input */}
                    {langConfig.depsPlaceholder && (
                        <div className="deps-bar">
                            <span className="deps-label">📦 Dependencies</span>
                            <input
                                type="text"
                                className="deps-input"
                                placeholder={langConfig.depsPlaceholder}
                                value={depsInput}
                                onChange={e => setDepsInput(e.target.value)}
                                id="deps-input"
                            />
                        </div>
                    )}

                    <div className="editor-actions">
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                                className="btn btn-primary"
                                onClick={handleRun}
                                disabled={isRunning || !code.trim()}
                                id="run-button"
                            >
                                {isRunning ? (
                                    <><span className="spinner" /> Running...</>
                                ) : (
                                    <><span className="btn-icon">▶</span> Run Code</>
                                )}
                            </button>
                            <button className="btn btn-secondary" onClick={handleClear} id="clear-button">
                                Clear
                            </button>
                        </div>
                        <div className="execution-meta">
                            <span>⌘+Enter to run</span>
                            {output?.execution_time_ms && (
                                <span>⏱ {output.execution_time_ms.toFixed(0)}ms</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right: Output Panel */}
                <div className="output-panel">
                    <div className="panel-header" style={{ padding: 0 }}>
                        <div className="output-tabs">
                            <button className={`output-tab ${activeTab === 'output' ? 'active' : ''}`}
                                onClick={() => setActiveTab('output')}>Output</button>
                            <button className={`output-tab ${activeTab === 'stderr' ? 'active' : ''}`}
                                onClick={() => setActiveTab('stderr')}>Errors</button>
                            <button className={`output-tab ${activeTab === 'history' ? 'active' : ''}`}
                                onClick={() => setActiveTab('history')}>History ({history.length})</button>
                        </div>
                        {output && (
                            <div style={{ padding: '0 20px' }}>
                                <span className={`status-indicator ${output.status}`}>{output.status}</span>
                            </div>
                        )}
                    </div>

                    {activeTab === 'history' ? (
                        <div className="history-panel" style={{ flex: 1 }}>
                            <div className="history-list" style={{ maxHeight: 'none', height: '100%' }}>
                                {history.length === 0 ? (
                                    <div className="output-placeholder" style={{ padding: '40px' }}>
                                        <p>No executions yet</p>
                                    </div>
                                ) : (
                                    history.map((item) => (
                                        <div key={item.execution_id} className="history-item"
                                            onClick={() => handleHistoryClick(item.execution_id)}>
                                            <div className="history-item-left">
                                                <span className={`status-indicator ${item.status}`}>{item.status}</span>
                                                <span className="history-language">{item.language}</span>
                                            </div>
                                            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                                                {item.execution_time_ms && (
                                                    <span className="history-duration">{item.execution_time_ms.toFixed(0)}ms</span>
                                                )}
                                                <span className="history-time">{new Date(item.created_at).toLocaleTimeString()}</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="output-content">
                            {error ? (
                                <span className="error-text">❌ Error: {error}</span>
                            ) : output ? (
                                activeTab === 'output' ? (
                                    LANGUAGES[output.language]?.outputType === 'html' ? (
                                        <div className="iframe-container">
                                            <iframe
                                                title="Execution Output"
                                                srcDoc={output.stdout}
                                                sandbox="allow-scripts"
                                                className="preview-iframe"
                                            />
                                        </div>
                                    ) : (
                                        output.stdout || <span style={{ color: 'var(--text-muted)' }}>No output</span>
                                    )
                                ) : (
                                    output.stderr ? (
                                        <span className="error-text">{output.stderr}</span>
                                    ) : (
                                        <span style={{ color: 'var(--text-muted)' }}>No errors</span>
                                    )
                                )
                            ) : (
                                <div className="output-placeholder">
                                    <div className="icon">🚀</div>
                                    <p>Run your code to see the output here</p>
                                    <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Press ⌘+Enter or click "Run Code"</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default App;
