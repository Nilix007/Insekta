from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseNotModified)
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.middleware.csrf import get_token

from insekta.scenario.models import (Scenario, ScenarioRun, RunTaskQueue,
                                     InvalidSecret, calculate_secret_token,
                                     AVAILABLE_TASKS)
from insekta.scenario.creole import render_scenario

@login_required
def scenario_home(request):
    """Show an users running/suspended vms and other informations."""
    return TemplateResponse(request, 'scenario/home.html', {

    })

@login_required
def scenario_groups(request):
    """Show an overview of the scenarios in groups."""
    return TemplateResponse(request, 'scenario/groups.html', {

    })

@login_required
def all_scenarios(request):
    """Show all scenarios as list."""
    return TemplateResponse(request, 'scenario/all.html', {
        'scenario_list': Scenario.objects.filter(enabled=True)
    })

@login_required
def show_scenario(request, scenario_name):
    """Shows the description of a scenario."""
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)

    try:
        scenario_run = ScenarioRun.objects.get(user=request.user,
                                               scenario=scenario)
        vm_state = scenario_run.state
        ip = scenario_run.address.ip
    except ScenarioRun.DoesNotExist:
        vm_state = 'disabled'
        ip = None

    environ = {
        'ip': ip,
        'user': request.user,
        'enter_secret_target': reverse('scenario.submit_secret',
                                       args=(scenario_name, )),
        'submitted_secrets': scenario.get_submitted_secrets(request.user),
        'all_secrets': scenario.get_secrets(),
        'secret_token_function': calculate_secret_token,
        'csrf_token': get_token(request)

    }
    return TemplateResponse(request, 'scenario/show.html', {
        'scenario': scenario,
        'description': render_scenario(scenario.description, environ=environ),
        'vm_state': vm_state,
        'ip': ip
    })

@login_required
def manage_vm(request, scenario_name):
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)
    
    try:
        scenario_run = ScenarioRun.objects.get(user=request.user,
                                               scenario=scenario)
    except ScenarioRun.DoesNotExist:
        scenario_run = scenario.start(request.user)
   
    # GET will check whether the action was executed
    if request.method == 'GET' and 'task_id' in request.GET:
        task_id = request.GET['task_id']
        if not RunTaskQueue.objects.filter(pk=task_id).count():
            return TemplateResponse(request, 'scenario/vmbox_dynamic.html', {
                'scenario': scenario,
                'vm_state': scenario_run.state,
                'ip': scenario_run.address.ip
            })
        else:
            return HttpResponseNotModified()
    # while POST asks the daemon to execute the action
    elif request.method == 'POST':
        action = request.POST.get('action')

        if not action or action not in AVAILABLE_TASKS:
            raise HttpResponseBadRequest('Action not available')

        # FIXME: Implement some way to prevent spamming (aka. DoS)
        # Checking is done in the daemon, here we just assume that
        # everything will work fine
        task = RunTaskQueue.objects.create(scenario_run=scenario_run,
                                           action=action)
        if request.is_ajax():
            return HttpResponse('{{"task_id": {0}}}'.format(task.pk),
                                mimetype='application/x-json')
        else:
            messages.success(request, _('Task was received and will be executed.'))
    
    return redirect(reverse('scenario.show', args=(scenario_name, )))


@login_required
def submit_secret(request, scenario_name):
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)
    try:
        scenario.submit_secret(request.user, request.POST.get('secret'),
                               request.POST.getlist('secret_token'))
    except InvalidSecret, e:
        messages.error(request, str(e))
    else:
        messages.success(request, _('Congratulation! Your secret was valid.'))

    return redirect(reverse('scenario.show', args=(scenario_name, )))
