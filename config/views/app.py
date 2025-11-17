from django.shortcuts import render

def app_view(request):
    """Serve the app.js page."""
    return render(request, 'app.html')
