from pyramid.config import Configurator
from ConfigParser import ConfigParser
from zope.component import getSiteManager
from pysiphae.root import root_factory
from pysiphae import views
from pysiphae.processmgr.payload import ProcessManager
from pysiphae import requestmethods
from pyramid.session import SignedCookieSessionFactory
import yaml
import uuid

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.hook_zca()
    config.include('pyramid_zcml')
    config.load_zcml('pysiphae:configure.zcml')
    config.include('pyramid_chameleon')
    config.include('pyramid_viewgroup')

    sessionfactory = SignedCookieSessionFactory(uuid.uuid4().hex)

    config.set_session_factory(sessionfactory)

    pconfig = yaml.load(
            open(settings.get('pysiphae.config')).read())
    config.registry.settings['pysiphae'] = pconfig
    default_permission = pconfig.get('default_permission', None)
    if default_permission:
        config.set_default_permission(default_permission)
    config.set_root_factory(root_factory)

    # register process managers
    processmgrs = pconfig.get('processmanagers', [])
    if not processmgrs:
        processmgrs.append({'name': 'defaut', 
                            'address': 'http://localhost:8888'})

    for pm in processmgrs:
        name = pm['name']
        address = pm['address']
        if name == 'default':
            config.registry.registerUtility(ProcessManager(address))
        else:
            config.registry.registerUtility(ProcessManager(address), name=name)

    # viewgroups
    for vg in pconfig.get('viewgroups', []):
        vg['context'] = vg.get('context', 'pysiphae.interfaces.ISiteRoot')
        config.add_viewgroup(**vg)

    config.add_static_view('++static++', 'static', cache_max_age=3600)
    config.add_request_method(requestmethods.main_template, 'main_template', reify=True)
    config.add_request_method(requestmethods.vars, 'template_vars', property=True)
    config.add_request_method(requestmethods.main_navigation, 'main_navigation',
            property=True)
    config.add_request_method(requestmethods.viewgroup_provider, 'provider',
            property=True)
    config.add_request_method(requestmethods.pconfig, 'pconfig', property=True)
    config.add_route('home','/')
    config.add_route('login','/login')
    config.add_route('logout','/logout')
    config.scan()

    plugins = pconfig.get('plugins', [])
    for plugin in plugins:
        package = config.maybe_dotted(plugin)
        if getattr(package, 'configure', None):
            package.configure(config, settings)
        config.load_zcml(plugin + ':configure.zcml')
        config.scan(plugin)

    return config.make_wsgi_app()

