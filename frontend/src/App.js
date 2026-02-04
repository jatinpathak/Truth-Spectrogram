import { useState } from "react";
import "@/App.css";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Upload, Shield, Eye, EyeOff, Loader2 } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const LANGUAGES = ["Tamil", "English", "Hindi", "Malayalam", "Telugu"];

function App() {
  const [selectedLanguage, setSelectedLanguage] = useState("English");
  const [apiKey, setApiKey] = useState("sk_test_voice_detection_2026");
  const [showApiKey, setShowApiKey] = useState(false);
  const [audioFile, setAudioFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.includes('audio') && !file.name.endsWith('.mp3')) {
        toast.error("Please upload an MP3 audio file");
        return;
      }
      setAudioFile(file);
      setFileName(file.name);
      setResult(null);
    }
  };

  const convertToBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = (error) => reject(error);
    });
  };

  const analyzeVoice = async () => {
    if (!audioFile) {
      toast.error("Please upload an audio file first");
      return;
    }

    if (!apiKey) {
      toast.error("Please enter API key");
      return;
    }

    setAnalyzing(true);
    setResult(null);

    try {
      const audioBase64 = await convertToBase64(audioFile);

      const response = await axios.post(
        `${API}/voice-detection`,
        {
          language: selectedLanguage,
          audioFormat: "mp3",
          audioBase64: audioBase64
        },
        {
          headers: {
            "x-api-key": apiKey,
            "Content-Type": "application/json"
          }
        }
      );

      setResult(response.data);
      toast.success("Analysis complete!");
    } catch (error) {
      console.error("Analysis error:", error);
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        toast.error(detail.message || detail);
      } else {
        toast.error("Failed to analyze voice. Please try again.");
      }
    } finally {
      setAnalyzing(false);
    }
  };

  const isAI = result?.classification === "AI_GENERATED";
  const isHuman = result?.classification === "HUMAN";

  return (
    <div className="App min-h-screen">
      {/* Scanlines overlay */}
      <div className="scanlines"></div>

      {/* Header */}
      <header className="header">
        <div className="header-content">
          <Shield className="w-8 h-8 text-cyan-400" data-testid="header-logo" />
          <h1 className="header-title" data-testid="app-title">Truth Spectrogram</h1>
        </div>
        <p className="header-subtitle" data-testid="app-subtitle">AI Voice Detection System</p>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <div className="grid-container">
          {/* Upload Section */}
          <Card className="upload-card" data-testid="upload-section">
            <div className="card-header">
              <h2 className="card-title">Audio Analysis</h2>
              <p className="card-description">Upload MP3 file for voice authenticity verification</p>
            </div>

            <div className="card-content">
              {/* Language Selector */}
              <div className="input-group">
                <Label htmlFor="language" className="input-label">Language</Label>
                <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                  <SelectTrigger className="custom-select" data-testid="language-selector">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map((lang) => (
                      <SelectItem key={lang} value={lang} data-testid={`language-option-${lang.toLowerCase()}`}>
                        {lang}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* API Key Input */}
              <div className="input-group">
                <Label htmlFor="apiKey" className="input-label">API Key</Label>
                <div className="api-key-container">
                  <Input
                    id="apiKey"
                    type={showApiKey ? "text" : "password"}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="api-key-input"
                    placeholder="sk_test_..."
                    data-testid="api-key-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="api-key-toggle"
                    data-testid="api-key-toggle"
                  >
                    {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* File Upload */}
              <div className="input-group">
                <Label htmlFor="audioFile" className="input-label">Audio File (MP3)</Label>
                <div className="file-upload-container">
                  <label htmlFor="audioFile" className="file-upload-label" data-testid="file-upload-label">
                    <Upload className="w-5 h-5" />
                    <span>{fileName || "Choose MP3 file"}</span>
                  </label>
                  <input
                    id="audioFile"
                    type="file"
                    accept=".mp3,audio/mp3,audio/mpeg"
                    onChange={handleFileChange}
                    className="file-upload-input"
                    data-testid="audio-file-input"
                  />
                </div>
              </div>

              {/* Analyze Button */}
              <Button
                onClick={analyzeVoice}
                disabled={!audioFile || analyzing}
                className="analyze-button"
                data-testid="analyze-button"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  "Analyze Voice"
                )}
              </Button>
            </div>
          </Card>

          {/* Results Section */}
          {result && (
            <Card className={`results-card ${isAI ? 'ai-detected' : 'human-detected'}`} data-testid="results-section">
              <div className="card-header">
                <h2 className="card-title">Analysis Results</h2>
              </div>

              <div className="card-content">
                <div className="results-grid">
                  {/* Classification */}
                  <div className="result-box" data-testid="classification-box">
                    <p className="result-label">Classification</p>
                    <div className={`classification-badge ${isAI ? 'badge-ai' : 'badge-human'}`} data-testid="classification-badge">
                      {result.classification.replace('_', ' ')}
                    </div>
                  </div>

                  {/* Confidence Score */}
                  <div className="result-box" data-testid="confidence-box">
                    <p className="result-label">Confidence Score</p>
                    <div className="confidence-display" data-testid="confidence-score">
                      {(result.confidenceScore * 100).toFixed(0)}%
                    </div>
                    <Progress
                      value={result.confidenceScore * 100}
                      className={`confidence-bar ${isAI ? 'progress-ai' : 'progress-human'}`}
                      data-testid="confidence-progress"
                    />
                  </div>

                  {/* Language */}
                  <div className="result-box" data-testid="language-box">
                    <p className="result-label">Language</p>
                    <p className="result-value" data-testid="result-language">{result.language}</p>
                  </div>

                  {/* Explanation */}
                  <div className="result-box explanation-box" data-testid="explanation-box">
                    <p className="result-label">Analysis</p>
                    <p className="result-explanation" data-testid="result-explanation">{result.explanation}</p>
                  </div>
                </div>
              </div>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;