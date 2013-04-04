page {{ paged_results.cur }} of {{ paged_results.total_pages }} ({{paged_results.total_items}} articles in total)

{% for art in paged_results.items %}- {%module domain(art.permalink)%}: [{{art.headline}}]({{art.permalink}})
  ([unsourced.org page](http://unsourced.org/art/{{art.id}}))
{% end %}
