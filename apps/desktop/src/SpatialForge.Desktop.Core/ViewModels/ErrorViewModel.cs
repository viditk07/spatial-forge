namespace SpatialForge.Desktop.ViewModels;

public sealed class ErrorViewModel : ViewModelBase
{
    private string _title = "SpatialForge needs attention";
    private string _explanation = "An unexpected local error occurred.";
    private string _recommendedAction = "Review the details and retry.";
    private string? _technicalDetails;

    public string Title { get => _title; set => SetProperty(ref _title, value); }
    public string Explanation { get => _explanation; set => SetProperty(ref _explanation, value); }
    public string RecommendedAction
    {
        get => _recommendedAction;
        set => SetProperty(ref _recommendedAction, value);
    }
    public string? TechnicalDetails
    {
        get => _technicalDetails;
        set => SetProperty(ref _technicalDetails, value);
    }
}

