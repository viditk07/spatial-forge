using System.Collections.ObjectModel;
using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public enum ImageReviewFilter
{
    All,
    Good,
    Review,
    Excluded,
}

public sealed class ImageReviewViewModel : ViewModelBase
{
    private readonly ISpatialForgeApiClient _apiClient;
    private readonly List<ImageReviewItemViewModel> _allImages = [];
    private ImageReviewFilter _filter;
    private ImageReviewItemViewModel? _selectedImage;

    public ImageReviewViewModel(ISpatialForgeApiClient apiClient)
    {
        _apiClient = apiClient;
        ShowAllCommand = new RelayCommand(() => Filter = ImageReviewFilter.All);
        ShowGoodCommand = new RelayCommand(() => Filter = ImageReviewFilter.Good);
        ShowReviewCommand = new RelayCommand(() => Filter = ImageReviewFilter.Review);
        ShowExcludedCommand = new RelayCommand(() => Filter = ImageReviewFilter.Excluded);
    }

    public ObservableCollection<ImageReviewItemViewModel> VisibleImages { get; } = [];
    public RelayCommand ShowAllCommand { get; }
    public RelayCommand ShowGoodCommand { get; }
    public RelayCommand ShowReviewCommand { get; }
    public RelayCommand ShowExcludedCommand { get; }

    public ImageReviewFilter Filter
    {
        get => _filter;
        set
        {
            if (SetProperty(ref _filter, value))
            {
                ApplyFilter();
            }
        }
    }

    public ImageReviewItemViewModel? SelectedImage
    {
        get => _selectedImage;
        set => SetProperty(ref _selectedImage, value);
    }

    public async Task LoadAsync(string projectId) => await RunGuardedAsync(async () =>
    {
        _allImages.Clear();
        foreach (ImageAsset image in await _apiClient.GetImagesAsync(projectId))
        {
            ImageReviewItemViewModel item = new(
                image,
                included => _apiClient.SetImageIncludedAsync(image.Id, included));
            item.PropertyChanged += (_, args) =>
            {
                if (args.PropertyName == nameof(ImageReviewItemViewModel.IsIncluded))
                {
                    ApplyFilter();
                }
            };
            _allImages.Add(item);
        }
        ApplyFilter();
    });

    public void ApplyFilter()
    {
        IEnumerable<ImageReviewItemViewModel> filtered = Filter switch
        {
            ImageReviewFilter.Good => _allImages.Where(image => image.QualityStatus == "good"),
            ImageReviewFilter.Review => _allImages.Where(
                image => image.IsIncluded && image.QualityStatus != "good"),
            ImageReviewFilter.Excluded => _allImages.Where(image => !image.IsIncluded),
            _ => _allImages,
        };
        VisibleImages.Clear();
        foreach (ImageReviewItemViewModel image in filtered)
        {
            VisibleImages.Add(image);
        }
    }
}

public sealed class ImageReviewItemViewModel : ObservableObject
{
    private readonly Func<bool, Task<ImageAsset>> _setIncluded;
    private ImageAsset _image;
    private bool _isIncluded;
    private bool _confirmedIncluded;
    private string? _inclusionError;

    public ImageReviewItemViewModel(
        ImageAsset image,
        Func<bool, Task<ImageAsset>> setIncluded)
    {
        _image = image;
        _isIncluded = image.Included;
        _confirmedIncluded = image.Included;
        _setIncluded = setIncluded;
        SaveInclusionCommand = new AsyncRelayCommand(SaveInclusionAsync);
    }

    public string Id => _image.Id;
    public string OriginalFilename => _image.OriginalFilename;
    public string? ThumbnailPath => _image.ThumbnailPath;
    public int Width => _image.Width;
    public int Height => _image.Height;
    public string QualityStatus => _image.QualityStatus;
    public double? FocalLengthMm => _image.FocalLengthMm;
    public ImageQuality? QualityMetric => _image.QualityMetric;
    public string WarningExplanation
    {
        get
        {
            if (QualityMetric is null)
            {
                return "Quality analysis has not run yet.";
            }

            List<string> warnings = [];
            if (QualityMetric.BlurScore is < 100)
            {
                warnings.Add("This photograph may be too blurred for reliable feature matching.");
            }
            if (QualityMetric.ExposureStatus is not null and not "good")
            {
                warnings.Add(QualityMetric.ExposureStatus switch
                {
                    "severe_underexposure" => "Large areas are severely underexposed.",
                    "severe_overexposure" => "Large areas are severely overexposed.",
                    "clipped_highlights" => "Bright detail appears clipped.",
                    "low_dynamic_range" => "The photograph has very little tonal contrast.",
                    _ => "Exposure may reduce reconstruction quality.",
                });
            }
            if (QualityMetric.ResolutionStatus == "low")
            {
                warnings.Add("Resolution is below the configured minimum dimension.");
            }
            if (QualityMetric.FeatureCountEstimate is < 500)
            {
                warnings.Add("Few visual features were estimated; blank surfaces may not match.");
            }
            if (QualityMetric.LensConsistencyStatus is not null and not "consistent")
            {
                warnings.Add(QualityMetric.LensConsistencyStatus == "mixed_focal_lengths"
                    ? "This project mixes focal lengths or phone lenses."
                    : "Image dimensions changed within this capture set.");
            }
            if (QualityMetric.DuplicateGroupId is not null)
            {
                warnings.Add("This photograph belongs to a near-duplicate group.");
            }

            return warnings.Count == 0
                ? "No significant quality warnings were detected."
                : string.Join(" ", warnings);
        }
    }

    public bool IsIncluded
    {
        get => _isIncluded;
        set => SetProperty(ref _isIncluded, value);
    }

    public AsyncRelayCommand SaveInclusionCommand { get; }
    public string? InclusionError
    {
        get => _inclusionError;
        private set => SetProperty(ref _inclusionError, value);
    }

    private async Task SaveInclusionAsync()
    {
        try
        {
            InclusionError = null;
            _image = await _setIncluded(IsIncluded);
            _confirmedIncluded = _image.Included;
            IsIncluded = _confirmedIncluded;
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            IsIncluded = _confirmedIncluded;
            InclusionError = error.Message;
        }
    }
}
