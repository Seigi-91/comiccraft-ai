param([ValidateRange(1024,65535)][int]$Port = 8000, [ValidateSet('','studio')][string]$OpenPath = '')
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
        if ($response.StatusCode -eq 200) { Start-Process "http://127.0.0.1:$Port/$OpenPath"; exit 0 }
    } catch { }
    Start-Sleep -Seconds 1
}
