from aiogram import Dispatcher

from modules.force_join.router import router as force_join_router

from modules.start.router import router as start_router

from modules.shop.router import router as shop_router
from modules.catalog.categories.router import router as categories_router
from modules.catalog.products.router import router as products_router
from modules.checkout.router import router as checkout_router
from modules.checkout.receipt import router as receipt_router
from modules.checkout.admin_review import router as admin_review_router
from modules.support.router import router as support_router
from modules.vpn.router import router as vpn_router
from modules.vpn.panel.admin.router import router as vpn_panel_admin_router
from modules.referral.router import router as referral_router
from modules.admin.updates import router as updates_router
from modules.admin.reseller_panel import router as reseller_panel_router
from modules.admin.agency_setup import router as agency_setup_router
from modules.admin.agency_bots import router as agency_bots_router
from modules.admin.catalog import router as admin_catalog_router
from modules.admin.operations import router as admin_operations_router
from modules.admin.router import router as admin_dashboard_router


def register_routers(dp: Dispatcher):

    dp.include_router(reseller_panel_router)
    dp.include_router(agency_setup_router)
    dp.include_router(force_join_router)

    dp.include_router(categories_router)

    dp.include_router(products_router)

    dp.include_router(checkout_router)

    dp.include_router(receipt_router)

    dp.include_router(admin_review_router)

    dp.include_router(support_router)

    dp.include_router(vpn_router)

    dp.include_router(vpn_panel_admin_router)

    dp.include_router(referral_router)

    dp.include_router(agency_bots_router)
    dp.include_router(admin_catalog_router)
    dp.include_router(admin_operations_router)
    dp.include_router(updates_router)
    dp.include_router(admin_dashboard_router)

    dp.include_router(shop_router)

    dp.include_router(start_router)

