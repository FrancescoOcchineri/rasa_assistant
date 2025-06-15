using Microsoft.AspNetCore.Components;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace GuiRasa.Pages
{
    public partial class Index
    {
        string userMessage = string.Empty;
        List<(string Role, string Text)> chat = new();

        private string placeholderText = "";

        protected override async Task OnInitializedAsync()
        {
            placeholderText = await RasaService.AskRasaAsync("Ciao");
        }

        async Task SendMessage()
        {
            if (string.IsNullOrWhiteSpace(userMessage)) return;

            chat.Add(("Tu", userMessage));
            var reply = await RasaService.AskRasaAsync(userMessage);
            chat.Add(("TARS", reply));
            userMessage = string.Empty;
        }

        void ClearChat()
        {
            chat.Clear();
        }
    }
}
