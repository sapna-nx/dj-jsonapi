
from json_api import routers
from json_api.fantasy import views


router = routers.APIRouter()
router.register(r'authors', views.AuthorView)
router.register(r'series', views.SeriesView)
router.register(r'books', views.BookView)
router.register(r'chapters', views.ChapterView)
router.register(r'stores', views.StoreView)
router.register(r'photos', views.PhotoView)

urlpatterns = router.urls
