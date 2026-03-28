from django import template
register =template.Library()

@register.simple_tag(takes_context=True)
def sort_url(context, sort_key ):
    request=context["request"]
    current_sort=context.get("current_sort")
    current_dir=context.get("current_dir","asc")
    
    next_dir="desc" if (current_sort==sort_key and current_dir=="asc") else "asc"
    
    params=request.GET.copy()
    params["sort"]=sort_key
    params["dir"]=next_dir
    return f"?{params.urlencode()}"
