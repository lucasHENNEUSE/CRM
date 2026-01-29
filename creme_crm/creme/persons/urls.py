################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025    Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.urls import re_path

from creme import persons
from creme.creme_core.conf.urls import Swappable, swap_manager

from .views import address, contact, organisation

urlpatterns = [
    # Routes spécifiques EN PREMIER (avant les génériques)
    re_path(
        r'^contact/email-mass-send[/]?$',
        contact.email_mass_send,
        name='persons__email_mass_send',
    ),

    re_path(
        r'^contact/as_user/(?P<contact_id>\d+)[/]?$',
        contact.TransformationIntoUser.as_view(),
        name='persons__transform_contact_into_user',
    ),

    re_path(
        r'^contact/taxe[/]?$', 
        contact.taxe_view,
        name='persons__taxe',
    ),

    re_path(
        r'^organisation/managed[/]?$',
        organisation.ManagedOrganisationsAdding.as_view(),
        name='persons__orga_set_managed',
    ),
    re_path(
        r'^organisation/not_managed[/]?$',
        organisation.OrganisationUnmanage.as_view(),
        name='persons__orga_unset_managed',
    ),

    *swap_manager.add_group(
        persons.contact_model_is_custom,
        Swappable(
            re_path(
                r'^contacts[/]?$',
                contact.ContactsList.as_view(),
                name='persons__list_contacts',
            )
        ),
        Swappable(
            re_path(
                r'^contact/add[/]?$',
                contact.ContactCreation.as_view(),
                name='persons__create_contact',
            ),
        ),
        Swappable(
            re_path(
                r'^contact/add_related/(?P<orga_id>\d+)[/]?$',
                contact.RelatedContactCreation.as_view(),
                name='persons__create_related_contact',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^contact/add_related/(?P<orga_id>\d+)/(?P<rtype_id>[\w-]+)[/]?$',
                contact.RelatedContactCreation.as_view(),
                name='persons__create_related_contact',
            ),
            check_args=(1, 'idxxx'),
        ),
        Swappable(
            re_path(
                r'^contact/edit/(?P<contact_id>\d+)[/]?$',
                contact.ContactEdition.as_view(),
                name='persons__edit_contact',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^contact/(?P<contact_id>\d+)[/]?$',
                contact.ContactDetail.as_view(),
                name='persons__view_contact',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='persons',
    ).kept_patterns(),

    *swap_manager.add_group(
        persons.organisation_model_is_custom,
        Swappable(
            re_path(
                r'^organisations[/]?$',
                organisation.OrganisationsList.as_view(),
                name='persons__list_organisations',
            )
        ),
        Swappable(
            re_path(
                r'^organisation/add[/]?$',
                organisation.OrganisationCreation.as_view(),
                name='persons__create_organisation',
            ),
        ),
        Swappable(
            re_path(
                r'^organisation/edit/(?P<orga_id>\d+)[/]?$',
                organisation.OrganisationEdition.as_view(),
                name='persons__edit_organisation',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^organisation/(?P<orga_id>\d+)[/]?$',
                organisation.OrganisationDetail.as_view(),
                name='persons__view_organisation',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^leads_customers[/]?$',
                organisation.MyLeadsAndMyCustomersList.as_view(),
                name='persons__leads_customers',
            ),
        ),
        Swappable(
            re_path(
                r'^lead_customer/add[/]?$',
                organisation.CustomerCreation.as_view(),
                name='persons__create_customer',
            ),
        ),
        app_name='persons',
    ).kept_patterns(),

    *swap_manager.add_group(
        persons.address_model_is_custom,
        Swappable(
            re_path(
                r'^address/add/(?P<entity_id>\d+)[/]?$',
                address.AddressCreation.as_view(),
                name='persons__create_address',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^address/add/billing/(?P<entity_id>\d+)[/]?$',
                address.BillingAddressCreation.as_view(),
                name='persons__create_billing_address',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^address/add/shipping/(?P<entity_id>\d+)[/]?$',
                address.ShippingAddressCreation.as_view(),
                name='persons__create_shipping_address',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^address/edit/(?P<address_id>\d+)[/]?$',
                address.AddressEdition.as_view(),
                name='persons__edit_address',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='persons',
    ).kept_patterns(),
]