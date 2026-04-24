---
layout: default
title: Home
---

# Horizon

Horizon publishes AI-generated daily digests to this site.

## English Feed

[Subscribe to the English feed]({{ '/feed-en.xml' | relative_url }})

{% assign en_posts = site.posts | where: "lang", "en" %}
{% if en_posts.size > 0 %}
{% for post in en_posts limit:20 %}
- [{{ post.date | date: "%Y-%m-%d" }}]({{ post.url | relative_url }})
{% endfor %}
{% else %}
No English posts yet.
{% endif %}

## Chinese Feed

[Subscribe to the Chinese feed]({{ '/feed-zh.xml' | relative_url }})

{% assign zh_posts = site.posts | where: "lang", "zh" %}
{% if zh_posts.size > 0 %}
{% for post in zh_posts limit:20 %}
- [{{ post.date | date: "%Y-%m-%d" }}]({{ post.url | relative_url }})
{% endfor %}
{% else %}
No Chinese posts yet.
{% endif %}
