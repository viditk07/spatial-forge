using System.Globalization;
using System.Xml.Linq;
using Xunit;

namespace SpatialForge.Desktop.Core.Tests;

public sealed class ThemeResourceTests
{
    private static readonly XNamespace Presentation =
        "http://schemas.microsoft.com/winfx/2006/xaml/presentation";
    private static readonly XNamespace Xaml = "http://schemas.microsoft.com/winfx/2006/xaml";

    [Fact]
    public void DesignTokensContainRequiredSemanticResources()
    {
        XDocument document = Load("Resources", "DesignTokens.xaml");
        HashSet<string> keys = document.Descendants()
            .Select(element => (string?)element.Attribute(Xaml + "Key"))
            .Where(key => key is not null)
            .Cast<string>()
            .ToHashSet(StringComparer.Ordinal);

        string[] required =
        [
            "AppBackground", "SidebarBackground", "SurfacePrimary", "SurfaceElevated",
            "AccentPrimary", "AccentPrimaryHover", "AccentPrimaryPressed", "TextPrimary",
            "TextSecondary", "TextMuted", "TextDisabled", "BorderSubtle", "BorderStrong",
            "FocusOutline", "StatusSuccess", "StatusWarning", "StatusError",
        ];

        Assert.All(required, key => Assert.Contains(key, keys));
    }

    [Fact]
    public void PrimaryAndSecondaryTextMeetWcagAaContrast()
    {
        XDocument document = Load("Resources", "DesignTokens.xaml");
        Dictionary<string, string> colors = document.Descendants(Presentation + "Color")
            .ToDictionary(
                element => (string)element.Attribute(Xaml + "Key")!,
                element => element.Value,
                StringComparer.Ordinal);

        Assert.True(Contrast(colors["TextPrimaryColor"], colors["AppBackgroundColor"]) >= 4.5);
        Assert.True(Contrast(colors["TextSecondaryColor"], colors["SurfacePrimaryColor"]) >= 4.5);
        Assert.True(Contrast(colors["AccentPrimaryColor"], colors["AppBackgroundColor"]) >= 4.5);
    }

    [Fact]
    public void InteractiveControlsHaveExplicitDarkTemplatesAndFocusStates()
    {
        string xaml = File.ReadAllText(PathOf("Resources", "ControlStyles.xaml"));
        string[] controls =
        [
            "Button", "TextBox", "ComboBox", "CheckBox", "RadioButton", "ListBoxItem",
            "ProgressBar", "ToolTip", "ContextMenu", "MenuItem", "DataGrid", "ScrollBar",
        ];

        Assert.All(controls, control => Assert.Contains($"TargetType=\"{control}\"", xaml, StringComparison.Ordinal));
        Assert.Contains("FocusOutline", xaml, StringComparison.Ordinal);
        Assert.Contains("PART_Popup", xaml, StringComparison.Ordinal);
        Assert.Contains("SurfaceElevated", xaml, StringComparison.Ordinal);
    }

    [Fact]
    public void MajorViewsExposeAccessibleNamesAndAvoidLightNativeBackgrounds()
    {
        string[] files =
        [
            "DashboardView.xaml", "NewProjectView.xaml", "HardwareView.xaml",
            "ImageReviewView.xaml", "ProcessingView.xaml", "ModelReviewView.xaml",
            "SettingsView.xaml", "ErrorView.xaml",
        ];

        foreach (string file in files)
        {
            string xaml = File.ReadAllText(PathOf("Views", file));
            Assert.Contains("AutomationProperties.Name", xaml, StringComparison.Ordinal);
            Assert.DoesNotContain("Background=\"White\"", xaml, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("Background=\"#FFF", xaml, StringComparison.OrdinalIgnoreCase);
        }
    }

    private static XDocument Load(params string[] parts) => XDocument.Load(PathOf(parts));

    private static string PathOf(params string[] parts) => Path.Combine(
        [AppContext.BaseDirectory, "UiFixtures", .. parts]);

    private static double Contrast(string first, string second)
    {
        double lighter = Math.Max(Luminance(first), Luminance(second));
        double darker = Math.Min(Luminance(first), Luminance(second));
        return (lighter + 0.05) / (darker + 0.05);
    }

    private static double Luminance(string hex)
    {
        string value = hex.TrimStart('#');
        double red = Channel(value[0..2]);
        double green = Channel(value[2..4]);
        double blue = Channel(value[4..6]);
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
    }

    private static double Channel(string hex)
    {
        double value = int.Parse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture) / 255.0;
        return value <= 0.04045 ? value / 12.92 : Math.Pow((value + 0.055) / 1.055, 2.4);
    }
}
