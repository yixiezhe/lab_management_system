from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Acceptance
from .serializers import AcceptanceSerializer
from procurement.models import PurchaseRequest


class AcceptanceViewSet(viewsets.ViewSet):
    """
    Handles the creation and updating of acceptance/receipt information.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AcceptanceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        purchase_request = validated_data.get('purchase_request')

        # Permission checks
        if purchase_request.applicant != request.user:
            return Response({"detail": "You are not the applicant for this request and cannot perform this action."},
                            status=status.HTTP_403_FORBIDDEN)

        if purchase_request.status != 'paid':
            return Response({
                                "detail": f"This request has a status of '{purchase_request.get_status_display()}' and cannot be marked as received."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Use update_or_create to handle both new and existing records
        acceptance_instance, created = Acceptance.objects.update_or_create(
            purchase_request=purchase_request,
            defaults={
                'receiving_status': validated_data.get('receiving_status'),
                'acceptance_photo': validated_data.get('acceptance_photo'),
                'recorded_by': request.user
            }
        )

        # **THE FIX**: Update the main request's status regardless of whether the acceptance
        # record was created or updated.
        purchase_request.status = 'goods_received'
        purchase_request.save(update_fields=['status'])

        # Return the data of the created/updated instance
        final_serializer = self.get_serializer(instance=acceptance_instance)
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(final_serializer.data, status=response_status)

    def partial_update(self, request, pk=None, *args, **kwargs):
        try:
            acceptance_instance = Acceptance.objects.select_related('purchase_request').get(pk=pk)
        except Acceptance.DoesNotExist:
            return Response({"detail": "Acceptance record not found."}, status=status.HTTP_404_NOT_FOUND)

        purchase_request = acceptance_instance.purchase_request
        if purchase_request.applicant != request.user:
            return Response({"detail": "You are not the applicant for this request and cannot perform this action."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance=acceptance_instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_acceptance = serializer.save(recorded_by=request.user)

        final_serializer = self.get_serializer(instance=updated_acceptance)
        return Response(final_serializer.data, status=status.HTTP_200_OK)

    def get_serializer(self, *args, **kwargs):
        """Helper function to get a serializer instance."""
        return self.serializer_class(*args, **kwargs)