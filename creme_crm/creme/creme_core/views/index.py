################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import json
from contextlib import suppress
from django.db.models import Q

from ..models import BrickHomeLocation, BrickMypageLocation
from .generic.base import BricksView


class BaseHome(BricksView):
    bricks_reload_url_name = 'creme_core__reload_home_bricks'


class Home(BaseHome):
    template_name = 'creme_core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with suppress(Exception):
            from creme.activities.models import ActivityType, Activity
            from creme.persons import get_contact_model
            
            Contact = get_contact_model()
            contacts = list(Contact.objects.filter(is_deleted=False))

            # On cherche le type d'activité qui correspond à un Rendez-vous
            meeting_type = ActivityType.objects.filter(name__icontains='Rendez-vous').first()
            if meeting_type:
                context['MEETING_TYPE_ID'] = meeting_type.id
                
            # On récupère les activités en base de données pour l'affichage
            activities = []
            for act in Activity.objects.order_by('-id')[:500]:
                if getattr(act, 'is_deleted', False):
                    continue
                if getattr(act, 'start', None):
                    title = getattr(act, 'name', None) or getattr(act, 'title', None) or str(act)
                    title_lower = title.lower()
                    
                    matched_contact_id = None
                    for c in contacts:
                        fn = (getattr(c, 'first_name', '') or '').strip().lower()
                        ln = (getattr(c, 'last_name', '') or '').strip().lower()
                        if fn and ln and (f"{fn} {ln}" in title_lower or f"{ln} {fn}" in title_lower):
                            matched_contact_id = c.id
                            break
                            
                    activities.append({
                        'id': act.id,
                        'title': title,
                        'start': act.start.strftime('%Y-%m-%d'),
                        'time': act.start.strftime('%H:%M'),
                        'type_name': act.type.name.lower() if getattr(act, 'type', None) else 'evenements',
                        'contact_id': matched_contact_id,
                    })
            context['activities_json'] = json.dumps(activities)
        return context

    def get_brick_ids(self):
        user = self.request.user
        is_superuser = user.is_superuser

        role_q = (
            Q(role=None, superuser=True)
            if is_superuser else
            Q(role=user.role, superuser=False)
        )
        locs = BrickHomeLocation.objects.filter(
            role_q | Q(role=None, superuser=False)
        ).order_by('order')

        brick_ids = [
            loc.brick_id for loc in locs if loc.superuser
        ] if is_superuser else [
            loc.brick_id for loc in locs if loc.role_id
        ]

        if not brick_ids:
            brick_ids = [loc.brick_id for loc in locs]

        return brick_ids


class MyPage(BaseHome):
    template_name = 'creme_core/my_page.html'

    def get_brick_ids(self):
        return BrickMypageLocation.objects.filter(
            user=self.request.user,
        ).order_by('order').values_list('brick_id', flat=True)
