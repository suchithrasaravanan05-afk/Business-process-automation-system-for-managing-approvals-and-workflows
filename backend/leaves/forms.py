from django import forms
from .models import LeaveType, LeaveRequest
from .services import calculate_leave_days


class LeaveApplicationForm(forms.ModelForm):
    leave_type = forms.ModelChoiceField(
        queryset=LeaveType.objects.filter(is_active=True),
        empty_label="-- Select Leave Type --",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_leave_type'})
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_start_date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_end_date'})
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'State the reason for taking leave...',
            'id': 'id_reason'
        })
    )

    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            try:
                # Validates dates and computes days
                calculate_leave_days(start_date, end_date)
            except Exception as e:
                raise forms.ValidationError(str(e))

        return cleaned_data
