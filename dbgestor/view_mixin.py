from django.shortcuts import redirect

class DeleteNextUrlMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.GET.get('next', '')
        return context  
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        next_url = request.POST.get('next', '')
        response = super().delete(request, *args, **kwargs)
        if next_url:
            return redirect(next_url)
        return response
