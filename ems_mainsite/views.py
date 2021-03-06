from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.core import serializers
from ems_account.models import UserPermissionProfile
from .models import InternalCircular, CompanyType, CompanySecondType, CompanyInfo, CompanyInfoOverHead
from hqjy_ems.check_system import check_system_open
from .forms import CompanyInfoForm, CompanyInfoOverHeadForm, CompanyInfoEditForm, CompanyInfoOverHeadEditForm
import json
from itertools import chain


@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
def page_error(request):
    context = {}
    return render(request, 'error.html/', context)

#分页方法，需要传入request、每页需要的文章数、用于分页的文章总集合
def page_2_page(request, num_of_page, need_info_query):
    #分页处理
    paginator = Paginator(need_info_query, num_of_page) #分页处理，num_of_page代表每页的文章数
    #获取页面传来参数（第N页）
    page = request.GET.get('page')
    page_num = paginator.get_page(page)
    return page_num #返回一个分页后的数据集

#页码缩减方法
def page_2_range(page_num):
    #获取当前页码
    current_page = page_num.number
    #获取当前页码的前两页
    behind_page = list(range(max(current_page-2,1),current_page))
    #获取当前页码的后两页
    after_page = list(range(current_page,min(page_num.paginator.num_pages,current_page+2)+1))
    #组合页码列表
    page_range = behind_page + after_page

    #判断第一页或最后一页的页码，如果页码之间间隔超过2页，添加"..."
    if page_range[0] - 1 >= 2 :
        page_range.insert(0,"...")
    if page_num.paginator.num_pages - page_range[-1] >= 2 :
        page_range.append("...")
        
    #判断页码，添加第一页和最后一页
    if page_range[0] != 1:
        page_range.insert(0,1)
    if page_range[-1] != page_num.paginator.num_pages:
        page_range.append(page_num.paginator.num_pages)

    return page_range

@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
def index_query(request):
    context = {}
    user_level = UserPermissionProfile.objects.filter(
        user=request.user).values()[0].get('user_level_id')
    
    
    if request.method == 'GET':

        #传递公司信息及分页
        all_company_info = CompanyInfo.objects.select_related('company_type').select_related('company_second_type')
        all_company_overhead_info = CompanyInfoOverHead.objects.all().prefetch_related('company_tag')
        
        #测试
        # for a in all_company_overhead_info:
        #     print(a.company_info_id, a.company_tag.all())
        # print(all_company_overhead_info.values())

        #分页
        page_num = page_2_page(request, 8, all_company_info) #调用分页方法，4 - 代表每页的文章数
        page_range = page_2_range(page_num) #调用页码缩减方法，传入的是分页后的数据

        context['all_company_info'] = all_company_info
        context['all_company_overhead_info'] =all_company_overhead_info
        # #传递分页后的blog文章集合信息
        context['page_num'] = page_num
        # #缩减后的页码范围
        context['page_range'] = page_range

        context['user_level'] = user_level

    
    return render(request, "index_query.html", context)

#工作台主页视图
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
        notification_auto_revocation__gte=today, notification_revocation_flag=False)
    
    if request.method == 'GET':
        company_info = CompanyInfoForm()
        company_Info_over_head = CompanyInfoOverHeadForm()
        context['company_info'] = company_info
        context['company_Info_over_head'] = company_Info_over_head
        #传递公司信息及分页
        all_company_info = CompanyInfo.objects.select_related('company_type').select_related('company_second_type')
        all_company_overhead_info = CompanyInfoOverHead.objects.all().prefetch_related('company_tag')
        
        #测试
        # for a in all_company_overhead_info:
        #     print(a.company_info_id, a.company_tag.all())
        # print(all_company_overhead_info.values())

        #分页
        page_num = page_2_page(request, 8, all_company_info) #调用分页方法，4 - 代表每页的文章数
        page_range = page_2_range(page_num) #调用页码缩减方法，传入的是分页后的数据

        context['all_company_info'] = all_company_info
        context['all_company_overhead_info'] =all_company_overhead_info
        # #传递分页后的blog文章集合信息
        context['page_num'] = page_num
        # #缩减后的页码范围
        context['page_range'] = page_range

    context['user_level'] = user_level
    context['notification_list'] = notification_list
    


    #判断用户级别，是否有使用workbench的权限
    if user_level == 4:
        return redirect("index_query")
    else:
        return render(request, "index_workbench.html", context)

    
#显示指定的通知视图
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
    json_data = serializers.serialize("json", company_type, use_natural_foreign_keys=False)
    #print(json_data)
    return HttpResponse(json_data,content_type="application/json")

#获取企业二级分类信息-返回Json数据
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def get_company_second_type_data(request):
    company_type_id = request.POST.get('company_type_id')
    company_second_type = CompanySecondType.objects.filter(company_type_id=company_type_id)
    #print(company_second_type)
    json_data = serializers.serialize("json", company_second_type, use_natural_foreign_keys=False)
    return HttpResponse(json_data,content_type="application/json")

#提交录入用户主信息数据视图
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def input_data_submit(request):
    
    if request.method == 'POST':
        company_info_form = CompanyInfoForm(request.POST)
        # print(request.POST)
        # print(company_info_form.is_valid())
        company_type_id = request.POST.get('company_type')
        company_second_type_id = request.POST.get('company_second_type')
        # print(company_type_id, company_second_type_id)
        if company_info_form.is_valid():
            new_company_info_form = company_info_form.save(commit=False)
            new_company_info_form.company_name = company_info_form.cleaned_data['company_name']
            new_company_info_form.company_type_id = company_type_id
            new_company_info_form.company_second_type_id = company_second_type_id
            new_company_info_form.company_IDcard = company_info_form.cleaned_data['company_IDcard']
            new_company_info_form.contact_phone = company_info_form.cleaned_data['contact_phone']
            new_company_info_form.save()
            #转换页面视图至用户附加信息
            ci_id = new_company_info_form.pk
            return HttpResponseRedirect(reverse('input_overhead_data_submit', args=[ci_id]))
        else:
            context = {}
            context ['company_info'] = company_info_form
            return render(request, 'index_workbench.html', context)

#提交录入用户附加信息数据视图
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def input_overhead_data_submit(request, ci_id):
    context = {}
    if request.method == 'GET':
         company_overhead_info_form = CompanyInfoOverHeadForm()
         user_level = UserPermissionProfile.objects.filter(user=request.user).values()[0].get('user_level_id')
         ci_id = ci_id
         context['ci_id'] = ci_id
         context['user_level'] = user_level
         context['company_info'] = company_overhead_info_form
         return render(request, "index_workbench.html", context)
    elif request.method == 'POST':
        company_overhead_info_form = CompanyInfoOverHeadForm(request.POST)
        company_tag_list = request.POST.getlist("company_tag")

        if company_overhead_info_form.is_valid():
            new_company_oh_info_form = company_overhead_info_form.save(commit=False)
            new_company_oh_info_form.company_info_id_id = ci_id
            new_company_oh_info_form.company_employee = company_overhead_info_form.cleaned_data['company_employee']
            new_company_oh_info_form.company_senior_staff = company_overhead_info_form.cleaned_data['company_senior_staff']
            new_company_oh_info_form.company_job_title = company_overhead_info_form.cleaned_data['company_job_title']
            new_company_oh_info_form.company_annual_income = company_overhead_info_form.cleaned_data['company_annual_income']
            new_company_oh_info_form.save()

            for company_tag_id in company_tag_list:
                new_company_oh_info_form.company_tag.add(company_tag_id)
                new_company_oh_info_form.save()

            return HttpResponseRedirect(reverse('index_workbench'))
        else:
            context = {}
            user_level = UserPermissionProfile.objects.filter(user=request.user).values()[0].get('user_level_id')
            ci_id = ci_id
            context['ci_id'] = ci_id
            context['user_level'] = user_level
            context['company_info'] = company_overhead_info_form
            context ['company_info'] = company_overhead_info_form
            return render(request, 'index_workbench.html', context)
            
    else:
        pass 

#查询框体视图
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def query_company_info(request):
    return render(request, '/ems_mainsite/workbench/search_data.html')

#获取所有公司信息视图 ---- 用此方法无法分页，已废弃
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def get_all_company_info(request):
    if request.method == "POST":
        all_company_info = CompanyInfo.objects.select_related('company_type').select_related('company_second_type')
        #分页
        page_num = page_2_page(request, 8, all_company_info) #调用分页方法，4 - 代表每页的文章数
        page_range = page_2_range(page_num) #调用页码缩减方法，传入的是分页后的数据
        print(page_num, page_range)
        json_data = serializers.serialize("json", page_num, use_natural_foreign_keys=True)
        print(json_data)
        return HttpResponse(json_data, content_type="application/json")
    elif request.method == "GET":
        all_company_info = CompanyInfo.objects.select_related('company_type').select_related('company_second_type')
        #分页
        page_num = page_2_page(request, 8, all_company_info) #调用分页方法，4 - 代表每页的文章数
        page_range = page_2_range(page_num) #调用页码缩减方法，传入的是分页后的数据
        context = {}
        context['all_company_info'] = all_company_info
        # #传递分页后的blog文章集合信息
        context['page_num'] = page_num
        # #缩减后的页码范围
        context['page_range'] = page_range
        return render(request, 'index_workbench.html', context)

#展示选中的公司视图
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def company_info_detail(request, ci_id):
    context = {}

    company_info = CompanyInfo.objects.filter(pk=ci_id).select_related('company_type').select_related('company_second_type')
    company_overhead_info = CompanyInfoOverHead.objects.filter(company_info_id=ci_id).prefetch_related('company_tag')
    
    #测试
    # for a in company_overhead_info:
    #     print(a.company_info_id, a.company_tag.all())

    context['company_info'] = company_info
    context['company_overhead_info'] = company_overhead_info
    
    return render(request, 'ems_mainsite/workbench/company_info_detail.html', context)

# 修改选中的企业信息并保存
@login_required(login_url='user_login')
@check_system_open(redirect='/system_maintenance/')
@csrf_exempt
def company_info_modify(request, ci_id):
    context = {}
    company_info = CompanyInfo.objects.filter(pk=ci_id).select_related('company_type').select_related('company_second_type')
    company_overhead_info = CompanyInfoOverHead.objects.filter(company_info_id=ci_id).prefetch_related('company_tag')
    
    # for c_tag in company_overhead_info:
    #     print(c_tag.company_tag.all())
    #定义企业基本信息初始化字典
    company_info_initial = {}
    #初始化赋值
    for com_info in company_info:
        #company_info_initial['company_name'] = com_info.company_name
        #因为以下2个type是用vue.js来实现的，所以这里不能初始化，意味着暂时无法修改，可以通过后台修改
        # company_info_initial['company_type'] = com_info.company_type
        # company_info_initial['company_second_type'] = com_info.company_second_type
        company_info_initial['company_area'] = com_info.company_area
        #company_info_initial['company_IDcard'] = com_info.company_IDcard
        company_info_initial['company_business_scope'] = com_info.company_business_scope
        company_info_initial['company_registered_capital'] = com_info.company_registered_capital
        company_info_initial['responsible_person'] = com_info.responsible_person
        #company_info_initial['responsible_person_phone'] = com_info.responsible_person_phone
        company_info_initial['responsible_person_sex'] = com_info.responsible_person_sex
        company_info_initial['responsible_person_age'] = com_info.responsible_person_age
        company_info_initial['responsible_person_politics_status'] = com_info.responsible_person_politics_status
        company_info_initial['responsible_person_education'] = com_info.responsible_person_education
        company_info_initial['contact_name'] = com_info.contact_name
        #company_info_initial['contact_phone'] = com_info.contact_phone
        company_info_initial['contact_email'] = com_info.contact_email
        company_info_initial['company_web'] = com_info.company_web
        company_info_initial['contact_address'] = com_info.contact_address

    #定义企业附加信息初始化字典
    company_overhead_info_initial = {}
    #初始化赋值
    for com_oh_info in company_overhead_info:
        #这里注意company_tag，必须使用all()方法，否则会报TypeError
        company_overhead_info_initial['company_tag'] = com_oh_info.company_tag.all()
        company_overhead_info_initial['company_employee'] = com_oh_info.company_employee
        company_overhead_info_initial['company_senior_staff'] = com_oh_info.company_senior_staff
        company_overhead_info_initial['company_job_title'] = com_oh_info.company_job_title
        company_overhead_info_initial['company_patents_number'] = com_oh_info.company_patents_number
        company_overhead_info_initial['company_product'] = com_oh_info.company_product
        company_overhead_info_initial['company_annual_income'] = com_oh_info.company_annual_income
        company_overhead_info_initial['company_remark'] = com_oh_info.company_remark

    #测试
   # print(company_overhead_info_initial)

    #GET方法用于渲染修改页面的表单
    if request.method == "GET":
        #初始化数据
        company_info_form = CompanyInfoEditForm(initial=company_info_initial)
        company_overhead_info_form = CompanyInfoOverHeadEditForm(initial=company_overhead_info_initial)

        context['company_info'] = company_info
        context['company_overhead_info'] = company_overhead_info

        context['company_info_form'] = company_info_form
        context['company_overhead_info_form'] = company_overhead_info_form

    #POST方法用于提交修改后的数据
    elif request.method == "POST":
        company_info = CompanyInfo.objects.get(pk=ci_id)
        company_overhead_info = CompanyInfoOverHead.objects.get(company_info_id=ci_id)
        company_info_form = CompanyInfoEditForm(request.POST)
        company_overhead_info_form = CompanyInfoOverHeadEditForm(request.POST)
        company_tag_list = request.POST.getlist("company_tag")

        #测试
        # print(company_info, company_overhead_info, company_tag_list)
        # print(company_info_form.is_valid(),company_overhead_info_form.is_valid())
        # print(company_info_form)

        if company_info_form.is_valid() * company_overhead_info_form.is_valid():

            company_info_cd = company_info_form.cleaned_data
            company_overhead_info_cd = company_overhead_info_form.cleaned_data

            #company_info校验数据
            company_info.company_area = company_info_cd['company_area']
            company_info.company_business_scope = company_info_cd['company_business_scope']
            company_info.company_registered_capital = company_info_cd['company_registered_capital']
            company_info.responsible_person = company_info_cd['responsible_person']
            company_info.responsible_person_sex = company_info_cd['responsible_person_sex']
            company_info.responsible_person_age = company_info_cd['responsible_person_age']
            company_info.responsible_person_politics_status = company_info_cd['responsible_person_politics_status']
            company_info.responsible_person_education = company_info_cd['responsible_person_education']
            company_info.contact_name = company_info_cd['contact_name']
            company_info.contact_email = company_info_cd['contact_email']
            company_info.company_web = company_info_cd['company_web']
            company_info.contact_address = company_info_cd['contact_address']

            #company_overhead_info校验数据 
            company_overhead_info.company_employee = company_overhead_info_cd['company_employee']
            company_overhead_info.company_senior_staff = company_overhead_info_cd['company_senior_staff']
            company_overhead_info.company_job_title = company_overhead_info_cd['company_job_title']
            company_overhead_info.company_patents_number = company_overhead_info_cd['company_patents_number']
            company_overhead_info.company_product = company_overhead_info_cd['company_product']
            company_overhead_info.company_annual_income = company_overhead_info_cd['company_annual_income']
            company_overhead_info.company_remark = company_overhead_info_cd['company_remark']

            #更新新tag
            #company_tags_obj = CompanyInfoOverHead.objects.filter(id__in=company_tag_list)
            company_overhead_info.company_tag.clear()
            company_overhead_info.company_tag.add(*company_tag_list)
 


            #开始写
            # for ci_item in company_info:
            #     print(ci_item)
            #     ci_item.save()
            company_info.save()
            
            # for chi_item in company_overhead_info:
            #     print(chi_item)
            #     chi_item.save()
            company_overhead_info.save()

            return HttpResponseRedirect(reverse('company_info_detail', args=[ci_id]))

        else:
            return HttpResponseRedirect(reverse('page_error'))

    else:
        print("系统出错啦！")

    return render(request, 'ems_mainsite/workbench/company_info_modify.html', context)