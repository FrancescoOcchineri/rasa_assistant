using Microsoft.AspNetCore.Components;

namespace GuiRasa.Shared
{
    public partial class MainLayout
    {
        [Inject]
        private NavigationManager Nav { get; set; } = default!;

        private bool SidebarVisible { get; set; } = true;

        private void ToggleSidebar()
        {
            SidebarVisible = !SidebarVisible;
        }

        private void GoHome()
        {
            Nav.NavigateTo("/");
        }
        private void GoLog()
        {
            Nav.NavigateTo("/log");
        }

    }
}
