using Microsoft.AspNetCore.Components;
using Microsoft.JSInterop;
using System.Threading.Tasks;

namespace GuiRasa.Pages
{
    public partial class Log : IDisposable
    {
        private string logContent = "";
        private ElementReference logElement;

        [Inject]
        private IJSRuntime JS { get; set; }

        [Inject]
        private GuiRasa.Service.LogRasaService LogService { get; set; }

        protected override void OnInitialized()
        {
            LogService.OnNewLog += AppendLog;
        }

        private async void AppendLog(string newLog)
        {
            var lines = newLog.Split('\n');
            foreach (var line in lines)
            {
                logContent += FormatLogLine(line) + "<br />";
            }
            await InvokeAsync(StateHasChanged);
            await ScrollToBottomAsync();
        }

        private string FormatLogLine(string line)
        {
            var encoded = System.Net.WebUtility.HtmlEncode(line);

            if (line.Contains("\"parse_data_text\":"))
            {
                // Messaggio utente
                return $"<span style='color: #50fa7b;'>{encoded}</span>";
            }

            if (line.Contains("BotUttered") || line.Contains("utter_"))
            {
                // Risposta bot
                return $"<span style='color: #f1fa8c;'>{encoded}</span>";
            }

            if (line.Contains("ERROR"))
                return $"<span style='color: #ff5555;'>{encoded}</span>";

            if (line.Contains("DEBUG"))
                return $"<span style='color: #6272a4;'>{encoded}</span>";

            return encoded;
        }

        private bool _isDisposed = false;
        private async Task ScrollToBottomAsync()
        {
            if (!_isDisposed)
            {
                try
                {
                    await JS.InvokeVoidAsync("scrollToBottom", logElement);
                }
                catch (TaskCanceledException)
                {

                }
            }
        }
        public void Dispose()
        {
            _isDisposed = true;
            LogService.OnNewLog -= AppendLog;
        }

    }
}
