# BMO Setup Script for Windows
# Run this in PowerShell

Write-Host "🎮 Setting up BMO AI Agent..." -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Check Python version
Write-Host "`nChecking Python version..."
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.8+ from python.org" -ForegroundColor Red
    exit 1
}

# Check if Ollama is installed
Write-Host "`nChecking for Ollama..."
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Write-Host "✅ Ollama is installed" -ForegroundColor Green
    $ollamaVersion = ollama --version
    Write-Host "   Version: $ollamaVersion"
} else {
    Write-Host "❌ Ollama not found" -ForegroundColor Red
    Write-Host "`nPlease install Ollama from: https://ollama.com" -ForegroundColor Yellow
    Write-Host "After installation, run this script again." -ForegroundColor Yellow
    
    $openBrowser = Read-Host "`nOpen Ollama download page in browser? (y/n)"
    if ($openBrowser -eq "y") {
        Start-Process "https://ollama.com/download"
    }
    exit 1
}

# Install Python dependencies
Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install Python packages" -ForegroundColor Red
    exit 1
}

# Start Ollama service (in background)
Write-Host "`nStarting Ollama service..." -ForegroundColor Yellow
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden

Start-Sleep -Seconds 3

# Pull the AI model
Write-Host "`nDownloading AI model (this may take a few minutes)..." -ForegroundColor Yellow
ollama pull llama3.2:3b

Write-Host "`n================================" -ForegroundColor Green
Write-Host "✅ BMO setup complete!" -ForegroundColor Green
Write-Host "`nTo start BMO, run:" -ForegroundColor Cyan
Write-Host "  python bmo_main.py" -ForegroundColor White
Write-Host "`nFor text-only mode:" -ForegroundColor Cyan
Write-Host "  python bmo_main.py --text" -ForegroundColor White
Write-Host "`n🎮 Have fun with BMO! 💛" -ForegroundColor Yellow
