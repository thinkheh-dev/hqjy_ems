from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.core import serializers
from ems_account.models import UserPermissionProfile
from .models import InternalCircular, CompanyType, CompanySecondType
from hqjy_ems.check_system import check_system_open
from .froms import CompanyInfoForm, CompanyInfoOverHeadForm

# Create your views here.


@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
def index_query(request):
    context = {}
    return render(request, "index_query.html", context)


@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
def index_workbench(request):
    context = {}
    user_level = UserPermissionProfile.objects.filter(
        user=request.user).values()[0].get('user_level_id')

    #通知视图
    today = timezone.now().date()
    # 取得自动撤销日期大于当天的通知
    notification_list = InternalCircular.objects.filter(
        notification_auto_revocation__gt=today, notification_revocation_flag=False)
    
    if request.method == 'GET':
        company_info = CompanyInfoForm()
        company_Info_over_head = CompanyInfoOverHeadForm()

    context['user_level'] = user_level
    context['notification_list'] = notification_list
    context['company_info'] = company_info
    context['company_Info_over_head'] = company_Info_over_head


    #判断用户级别，是否有使用workbench的权限
    if user_level == 4:
        return redirect("index_query")
    else:
        return render(request, "index_workbench.html", context)

    

@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
def notification_detail(request, Internalcircular_pk):
    current_notification = get_object_or_404(InternalCircular, pk=Internalcircular_pk)
    context = {}
    context['current_notification'] = current_notification
    return render(request, "ems_mainsite/notification_detail.html", context)

#获取企业一级分类信息-返回Json数据
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def get_company_type_data(request):
    company_type = CompanyType.objects.all()
    json_data = serializers.serialize("json", company_type)
    return HttpResponse(json_data,content_type="application/json")

#获取企业二级分类信息-返回Json数据
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def get_company_second_type_data(request):
    company_type_id = request.POST.get('company_type_id')
    company_second_type = CompanySecondType.objects.filter(company_type_id=company_type_id)
    print(company_second_type)
    json_data = serializers.serialize("json", company_second_type)
    return HttpResponse(json_data,content_type="application/json")

