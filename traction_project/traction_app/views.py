from django.shortcuts import render
from django.db.models import Q
from .tasks import get_access_token, email_users
from .models import Item


def home(request):
    context = {}
    if request.user.is_authenticated:
        context = {
            'tracked_items': request.user.profile.tracked_items.all()
        }

    code = request.GET.get('code')
    if code:
        get_access_token.delay(request.user.id, code)

    item = request.GET.get('item')
    if item:
        request.user.profile.tracked_items.add(Item.objects.get(hash=item))
    ritem = request.GET.get('ritem')
    if ritem:
        request.user.profile.tracked_items.remove(Item.objects.get(name=ritem))

    return render(request, 'traction_app/home.html', context)


def about(request):
    email_users.delay()
    return render(request, 'traction_app/about.html', {'title': 'About'})


def search(request):
    query = request.GET.get('q')
    items = Item.objects.filter(Q(name__icontains=query))
    return render(
            request,
            'traction_app/search.html',
            {'title': 'Search', 'items': items}
            )
