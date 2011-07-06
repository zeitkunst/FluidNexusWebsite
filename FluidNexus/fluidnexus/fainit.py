from fluidnexus import models, faforms

def includeme(config):
    config.include('pyramid_formalchemy')
    # Adding the jquery libraries
    config.include('fa.jquery')
    # Adding the package specific routes
    config.include('fluidnexus.faroutes')

    try:
        # pyramid_alchemy
        session_factory = models.DBSession
    except AttributeError:
        # akhet
        session_factory = models.Session

    config.formalchemy_admin("/admin",
                             models=models,
                             forms=faforms,
                             session_factory=session_factory,
                             view="fa.jquery.pyramid.ModelView")
