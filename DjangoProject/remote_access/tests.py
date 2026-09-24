from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import MAX_REMOTE_BOOKING_DURATION, RdpBooking, RdpMachine


class RdpBookingInstantConnectTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='255393220',
            password='test-pass',
            name='示例成员16',
            email='song@example.com',
        )
        self.machine = RdpMachine.objects.create(
            name='land1',
            ip_address='127.0.0.1:0001',
            is_active=True,
            username='land1',
        )
        self.client.force_authenticate(self.user)

    def test_instant_connect_uses_server_time_instead_of_client_time(self):
        server_now = timezone.make_aware(
            timezone.datetime(2026, 6, 26, 18, 40, 0),
            timezone.get_current_timezone(),
        )
        stale_client_time = server_now - timezone.timedelta(hours=2)

        with patch('remote_access.views.timezone.now', return_value=server_now):
            response = self.client.post(
                '/api/remote_access/bookings/instant_connect/',
                {
                    'machine': self.machine.id,
                    'start_time': stale_client_time.isoformat(),
                    'end_time': (stale_client_time + MAX_REMOTE_BOOKING_DURATION).isoformat(),
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = RdpBooking.objects.get(pk=response.data['id'])
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.machine, self.machine)
        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(booking.start_time, server_now)
        self.assertEqual(booking.end_time, server_now + MAX_REMOTE_BOOKING_DURATION)
