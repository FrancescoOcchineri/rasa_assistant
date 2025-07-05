using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace GuiRasa.Service
{
   public class LogRasaService : IAsyncDisposable
    {
        private readonly string _logFilePath;
        private long _lastPosition = 0;
        private Timer _timer;

        public event Action<string> OnNewLog;

        public LogRasaService(string logFilePath)
        {
            _logFilePath = logFilePath;
            _timer = new Timer(ReadNewLogs, null, 0, 2000);
        }

        private void ReadNewLogs(object? state)
        {
            try
            {
                if (!File.Exists(_logFilePath))
                    return;

                using var stream = new FileStream(_logFilePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                stream.Seek(_lastPosition, SeekOrigin.Begin);

                using var reader = new StreamReader(stream);
                var newText = reader.ReadToEnd();

                if (!string.IsNullOrEmpty(newText))
                {
                    _lastPosition = stream.Position;
                    OnNewLog?.Invoke(newText);
                }
            }
            catch
            {

            }
        }

        public ValueTask DisposeAsync()
        {
            _timer?.Dispose();
            return ValueTask.CompletedTask;
        }
    }
}
