using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using GuiRasa; 

public class RasaService
{
    private readonly HttpClient _httpClient;
    private readonly string _endpoint;

    public RasaService(HttpClient httpClient)
    {
        _httpClient = httpClient;
        _endpoint = RasaConfig.Endpoint; 
    }

    public async Task<string> AskRasaAsync(string prompt)
    {
        var requestPayload = new
        {
            sender = "ciao",
            message = prompt
        };

        var content = new StringContent(JsonSerializer.Serialize(requestPayload), Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync(_endpoint, content);

        if (response.IsSuccessStatusCode)
        {
            var json = await response.Content.ReadAsStringAsync();

            var rasaResponses = JsonSerializer.Deserialize<List<RasaMessage>>(json);

            if (rasaResponses != null && rasaResponses.Any())
            {
                return string.Join("\n", rasaResponses.Select(r => r.Text));
            }
            else
            {
                return "Nessuna risposta da Rasa.";
            }
        }
        else
        {
            return "Errore nella richiesta a Rasa.";
        }
    }

    public class RasaMessage
    {
        [JsonPropertyName("recipient_id")]
        public string RecipientId { get; set; }

        [JsonPropertyName("text")]
        public string Text { get; set; }
    }
}
