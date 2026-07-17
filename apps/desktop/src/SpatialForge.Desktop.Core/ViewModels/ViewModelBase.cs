using SpatialForge.Desktop.Infrastructure;

namespace SpatialForge.Desktop.ViewModels;

public abstract class ViewModelBase : ObservableObject
{
    private bool _isBusy;
    private string? _errorMessage;

    public bool IsBusy
    {
        get => _isBusy;
        protected set => SetProperty(ref _isBusy, value);
    }

    public string? ErrorMessage
    {
        get => _errorMessage;
        protected set => SetProperty(ref _errorMessage, value);
    }

    protected async Task RunGuardedAsync(Func<Task> action)
    {
        IsBusy = true;
        ErrorMessage = null;
        try
        {
            await action().ConfigureAwait(true);
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            ErrorMessage = error.Message;
        }
        finally
        {
            IsBusy = false;
        }
    }
}

