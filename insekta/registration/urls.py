from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^login', 'django.contrib.auth.views.login'),
    url(r'^logout', 'django.contrib.auth.views.logout_then_login'),

    url(r'^password-reset-confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)$',  'django.contrib.auth.views.password_reset_confirm'),
    url(r'^password-reset$', 'django.contrib.auth.views.password_reset'),
    url(r'^password-reset-done$', 'django.contrib.auth.views.password_reset_done'),
    url(r'^password-reset-complete$', 'django.contrib.auth.views.password_reset_complete'),
)

urlpatterns += patterns('insekta.registration.views',
    url(r'^registration$', 'registration', name='registration.registration'),
    url(r'^pending/(\w+)/(\w+)$', 'pending', name='registration.pending'),
)
