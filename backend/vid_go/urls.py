"""
URL configuration for vid_go project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# vid_go/urls.py
import os
from django.contrib import admin
from django.urls import include,path,re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # 前端静态资源
    re_path(r'^assets/(?P<path>.*)$', views.frontend_assets, name='frontend_assets'),
    
    # 优先包含自定义媒体路由
    path('api/', include("video.urls"), name='video'),  # 将 /api/ 路径映射到 video 应用的路由
    path('api/auth/', include("accounts.urls"), name='accounts'),  # User authentication endpoints
    
    # Vue Router 的 history mode 支持 - 所有其他路径都返回前端应用
    re_path(r'^(?!api/|admin/|media/|static/).*$', views.index, name='frontend'),
]


# Serve media files during development
if settings.DEBUG:
    # 直接配置静态文件服务，将 /media/video/ 映射到 saved_video 目录
    urlpatterns += static('/media/video/', document_root=os.path.join(settings.MEDIA_ROOT, 'saved_video'))
    urlpatterns += static('/media/audio/', document_root=os.path.join(settings.MEDIA_ROOT, 'saved_audio'))
    # 其他媒体文件
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
