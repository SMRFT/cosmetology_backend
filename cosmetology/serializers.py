# forms.py
from rest_framework import serializers
from .models import Register
from bson import ObjectId

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)
    def to_internal_value(self, data):
        return ObjectId(data)
    

class RegisterSerializer(serializers.ModelSerializer):
    confirmPassword = serializers.CharField(write_only=True)
    
    class Meta:
        model = Register
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def validate(self, data):
        if data['password'] != data['confirmPassword']:
            raise serializers.ValidationError({"confirmPassword": "Passwords don't match"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirmPassword')
        
        # Convert branch_code array to objects with isactive status
        if 'branch_code' in validated_data and isinstance(validated_data['branch_code'], list):
            branch_objects = []
            for branch_code in validated_data['branch_code']:
                if isinstance(branch_code, str):
                    # Convert string to object format
                    branch_objects.append({
                        'branch_code': branch_code,
                        'isactive': True  # Default to active when registering
                    })
                elif isinstance(branch_code, dict):
                    # Already in object format
                    branch_objects.append(branch_code)
            validated_data['branch_code'] = branch_objects
        
        return Register.objects.create(**validated_data)

class BranchStatusSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    branch_code = serializers.CharField()
    isactive = serializers.BooleanField()
    
    
from .models import Login
class LoginSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model =   Login
        fields = '__all__'


from .models import Pharmacy
class PharmacySerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Pharmacy
        fields = '__all__'

class PharmacyStockUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacy
        fields = ['medicine_name', 'old_stock']  # Include only necessary fields


from .models import Patient
class PatientSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Patient
        fields = '__all__'


from .models import Appointment
class AppointmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Appointment
        fields = '__all__'


from .models import SummaryDetail
class SummaryDetailSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = SummaryDetail
        fields = '__all__'


from .models import Visit
class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = '__all__'


from .models import Vital
class VitalSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Vital
        fields = '__all__'


from .models import BillingData
class BillingDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingData
        fields = '__all__'


from .models import ProcedureBill
class ProcedureBillSerializer(serializers.ModelSerializer):
     id = ObjectIdField(read_only=True)
     class Meta:
        model = ProcedureBill
        fields = '__all__'


from .models import Diagnosis,Complaints,Findings,Tests,Procedure
class DiagnosisSerializer(serializers.ModelSerializer):
     id = ObjectIdField(read_only=True)
     class Meta:
        model = Diagnosis
        fields = '__all__'

class ComplaintsSerializer(serializers.ModelSerializer):
     id = ObjectIdField(read_only=True)
     class Meta:
        model = Complaints
        fields = '__all__'

class FindingsSerializer(serializers.ModelSerializer):
     id = ObjectIdField(read_only=True)
     class Meta:
        model = Findings
        fields = '__all__'

class TestsSerializer(serializers.ModelSerializer):
     id = ObjectIdField(read_only=True)
     class Meta:
        model = Tests
        fields = '__all__'

class ProcedureSerializer(serializers.ModelSerializer):
     id = ObjectIdField(read_only=True)
     class Meta:
        model = Procedure
        fields = '__all__'


