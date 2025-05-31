from rest_framework.views import APIView
from gridfs import GridFS
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.utils import timezone
import json
from decimal import Decimal
from bson.json_util import dumps, loads
from .models import ProcedureBill
from .serializers import ProcedureBillSerializer
from .models import BillingData
from .serializers import BillingDataSerializer
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
import logging


from .models import Pharmacy
from .models import Patient
from .models import Appointment  
from .serializers import VitalSerializer
from .models import Vital
from .models import Register
from .serializers import PharmacyStockUpdateSerializer
from .serializers import AppointmentSerializer
from .serializers import PatientSerializer
from .serializers import PharmacySerializer
from .models import Diagnosis,Complaints,Findings,Tests,Procedure
from .serializers import DiagnosisSerializer,ComplaintsSerializer,FindingsSerializer,TestsSerializer,ProcedureSerializer
from .models import SummaryDetail
from .serializers import SummaryDetailSerializer


from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo import MongoClient

import os
from dotenv import load_dotenv

load_dotenv() 

from .serializers import RegisterSerializer
from django.db import DatabaseError

@csrf_exempt
@api_view(['POST'])
def registration(request):
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except DatabaseError as e:
                import traceback
                print(traceback.format_exc())  # Logs the full traceback
                return Response({'error': 'Database error occurred.', 'details': str(e)}, status=500)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    

# MongoDB connection setup
client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
db = client['cosmetology']
branch_collection = db['cosmetology_branch']  

@api_view(['GET'])
def get_branches(request):
    try:
        # Directly fetch branches from MongoDB collection
        branches = list(branch_collection.find({}, {'_id': 0}))  # Exclude MongoDB _id
        
        # If you need to include _id, you need to serialize it properly
        # Convert MongoDB cursor to JSON compatible format
        branches_json = json.loads(dumps(branches))
        
        return Response(branches_json, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
from .models import Register
@api_view(['POST'])
@csrf_exempt
def login(request):
    if request.method == 'POST':
        username = request.data.get('username')
        password = request.data.get('password')
        endpoint = request.data.get('endpoint')

        try:
            user = Register.objects.get(id=username, password=password)
            
            # Extract branch code from the database
            branch_code = user.branch_code
            
            # Parse branch codes - handle both string format "[code1, code2]" and list format
            branch_codes = []
            if isinstance(branch_code, str):
                # Handle the JSON string format like "[\"SSC001\", \"SSC002\"]"
                try:
                    # Try to parse the JSON string
                    branch_codes = json.loads(branch_code)
                except json.JSONDecodeError:
                    # If it's not valid JSON but still has brackets, try to parse manually
                    if branch_code.startswith('[') and branch_code.endswith(']'):
                        # Remove brackets and split by comma
                        codes_str = branch_code[1:-1].replace('"', '').replace("'", "")
                        branch_codes = [code.strip() for code in codes_str.split(',')]
                    else:
                        # It's a single code
                        branch_codes = [branch_code]
            elif isinstance(branch_code, list):
                # It's already a list
                branch_codes = branch_code
            else:
                # Default to empty list
                branch_codes = []

            # Check if the user is authorized for the endpoint
            # Check endpoint restrictions (Doctor can log in from any endpoint)
            if user.role != 'Admin':
                if endpoint == 'AdminLogin' and user.role != 'Admin':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)
                elif endpoint == 'PharmacistLogin' and user.role != 'Pharmacist':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)
                elif endpoint == 'ReceptionistLogin' and user.role != 'Receptionist':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)
                elif endpoint == 'DoctorLogin' and user.role != 'Doctor':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)

            # Create response data
            response_data = {
                'message': 'Login successful',
                'role': user.role,
                'id': user.id,
                'name': user.name, 
                'contact': user.contact,
            }
            
            # Include branch codes in the response
            if len(branch_codes) == 1:
                # Single branch - include as branch_code for backward compatibility
                response_data['branch_code'] = branch_codes[0]
            
            # Always include the full list of branch codes
            response_data['branch_codes'] = branch_codes
            
            response = Response(response_data, status=status.HTTP_200_OK)
            
            # Set a cookie only if there's a single branch code
            if len(branch_codes) == 1:
                response.set_cookie('branch_code', branch_codes[0], max_age=7*24*60*60)  # 7 days
                
            return response
            
        except Register.DoesNotExist:
            return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)


        



logger = logging.getLogger(__name__)

@api_view(['GET', 'POST', 'PUT', 'PATCH'])
def pharmacy_data(request):
    # Get branch_code from request parameters or cookies
    branch_code = request.query_params.get('branch_code') or request.COOKIES.get('branch_code')
    
    if request.method == 'GET':
        # With branch code filtering
        if branch_code:
            medicines = Pharmacy.objects.filter(branch_code=branch_code)
        else:
            medicines = Pharmacy.objects.all()
        serializer = PharmacySerializer(medicines, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        # Add branch_code to each item if it's not present
        if isinstance(request.data, list):
            for item in request.data:
                if not item.get('branch_code') and branch_code:
                    item['branch_code'] = branch_code
        else:
            if not request.data.get('branch_code') and branch_code:
                request.data['branch_code'] = branch_code
                
        serializer = PharmacySerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'PATCH':
        response_data = []

        if not isinstance(request.data, list):
            request_data = [request.data]
        else:
            request_data = request.data

        # MongoDB connection
        client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
        db = client['cosmetology']
        pharmacy_collection = db.cosmetology_pharmacy

        for data in request_data:
            medicine_name = data.get('medicine_name')
            batch_number = data.get('batch_number')

            if not data.get('branch_code') and branch_code:
                data['branch_code'] = branch_code

            try:
                result = pharmacy_collection.update_one(
                    {
                        "medicine_name": medicine_name,
                        "batch_number": batch_number,
                        "branch_code": data.get('branch_code')
                    },
                    {"$set": data},
                    upsert=True
                )

                if result.matched_count > 0 or result.upserted_id:
                    response_data.append(data)
                else:
                    logger.error(f"Failed to update document with medicine_name={medicine_name}, batch_number={batch_number}")
                    return Response({'error': 'Failed to update the document.'}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                logger.error(f"Error updating medicine {medicine_name} (batch {batch_number}): {str(e)}")
                return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(response_data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        # If you still want to keep the full replace functionality 
        response_data = []
        client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
        db = client['cosmetology']
        pharmacy_collection = db.cosmetology_pharmacy

        # Clear existing data based on branch_code if provided
        if branch_code:
            pharmacy_collection.delete_many({'branch_code': branch_code})
        else:
            pharmacy_collection.delete_many({})

        for data in request.data:
            # Add branch_code to data if not present
            if not data.get('branch_code') and branch_code:
                data['branch_code'] = branch_code
                
            medicine_name = data.get('medicine_name')
            batch_number = data.get('batch_number')
            try:
                # Update or upsert the document in MongoDB
                result = pharmacy_collection.update_one(
                    {'medicine_name': medicine_name, 'batch_number': batch_number, 'branch_code': data.get('branch_code')},
                    {'$set': data},
                    upsert=True
                )
                if result.upserted_id or result.modified_count > 0:
                    response_data.append(data)
                else:
                    logger.error(f"Failed to update document with medicine_name={medicine_name} and batch_number={batch_number}")
                    return Response({'error': 'Failed to update the document.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Unexpected error for medicine_name={medicine_name} and batch_number={batch_number}: {e}")
                return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(response_data, status=status.HTTP_200_OK)
    




# Setup MongoDB client
client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
db = client['cosmetology']
pharmacy_collection = db.cosmetology_pharmacy

@require_http_methods(["DELETE"])
@csrf_exempt
def delete_medicine(request, medicine_name):
    branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')

    query = {
        "medicine_name": medicine_name
    }
    if branch_code:
        query["branch_code"] = branch_code

    try:
        result = pharmacy_collection.delete_one(query)

        if result.deleted_count == 0:
            return JsonResponse({"error": "Medicine not found."}, status=404)

        return JsonResponse({"message": "Medicine deleted successfully."}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)




@api_view(['PUT'])
def update_stock(request):
    if request.method == 'PUT':
        data = request.data
        medicine_name = data.get('medicine_name')
        qty = data.get('qty')
        branch_code = data.get('branch_code') or request.COOKIES.get('branch_code')
        
        if not medicine_name or qty is None:
            return Response({'error': 'Invalid data. Medicine name and quantity are required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            qty = int(qty)  # Ensure qty is an integer
            # Correct MongoDB connection string
            client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
            db = client['cosmetology']
            pharmacy_collection = db.cosmetology_pharmacy
            
            # Find the document by medicine_name and branch_code if provided
            query = {'medicine_name': medicine_name}
            if branch_code:
                query['branch_code'] = branch_code
                
            document = pharmacy_collection.find_one(query)
            if not document:
                return Response({'error': 'Medicine not found'}, status=status.HTTP_404_NOT_FOUND)
            old_stock = document.get('old_stock', 0)
            new_stock = old_stock - qty
            if new_stock < 0:
                return Response({'error': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)
            # Update the stock
            result = pharmacy_collection.update_one(
                query,
                {'$set': {'old_stock': new_stock}}
            )
            if result.matched_count == 0:
                return Response({'error': 'Failed to update stock'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'message': 'Stock updated successfully'}, status=status.HTTP_200_OK)
        except ValueError:
            return Response({'error': 'Invalid quantity value'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def pharmacy_upload(request):
    branch_code = request.data.get('branch_code') or request.COOKIES.get('branch_code')
    
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        # Store branch_code with file info if needed
        # Handle file upload logic here
        return Response({'message': 'File uploaded successfully', 'branch_code': branch_code}, status=status.HTTP_201_CREATED)
    return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
def check_medicine_status(request):
    branch_code = request.query_params.get('branch_code') or request.COOKIES.get('branch_code')
    
    low_quantity_medicines = []
    near_expiry_medicines = []

    # Filter by branch_code if provided
    if branch_code:
        medicines = Pharmacy.objects.filter(branch_code=branch_code)
    else:
        medicines = Pharmacy.objects.all()

    for medicine in medicines:
        if medicine.is_quantity_low():
            low_quantity_medicines.append(medicine)
        if medicine.is_expiry_near():
            near_expiry_medicines.append(medicine)

    response_data = {
        'low_quantity_medicines': PharmacySerializer(low_quantity_medicines, many=True).data,
        'near_expiry_medicines': PharmacySerializer(near_expiry_medicines, many=True).data,
    }

    return Response(response_data, status=status.HTTP_200_OK)



@api_view(['POST', 'PATCH', 'DELETE'])
def Patients_data(request, patientUID=None):
    branch_code = request.data.get('branch_code') or request.COOKIES.get('branch_code')
    
    if request.method == 'POST':
        # Add branch_code to request data if not present
        if not request.data.get('branch_code') and branch_code:
            request.data['branch_code'] = branch_code
            
        serializer = PatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'PATCH':
        if not patientUID:
            return Response({"error": "patientUID is required in the URL"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Find patient by UID and branch_code if provided
            if branch_code:
                patient = Patient.objects.get(patientUID=patientUID, branch_code=branch_code)
            else:
                patient = Patient.objects.get(patientUID=patientUID)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Add branch_code to request data if not present
        if not request.data.get('branch_code') and branch_code:
            request.data['branch_code'] = branch_code
            
        serializer = PatientSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        if not patientUID:
            return Response({"error": "patientUID is required in the URL"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Delete patient by UID and branch_code if provided
            if branch_code:
                patient = Patient.objects.get(patientUID=patientUID, branch_code=branch_code)
            else:
                patient = Patient.objects.get(patientUID=patientUID)
            patient.delete()
            return Response({"message": "Patient deleted successfully"}, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)



@api_view(['GET'])
def PatientView(request):
    if request.method == 'GET':
        branch_code = request.query_params.get('branch_code') or request.COOKIES.get('branch_code')
        
        # Filter by branch_code if provided
        if branch_code:
            patients = Patient.objects.filter(branch_code=branch_code)
        else:
            patients = Patient.objects.all()
            
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)
    


@api_view(['POST'])
@csrf_exempt
def Appointmentpost(request):
    if request.method == 'POST':
        patient_uid = request.data.get('patientUID')
        appointment_date = request.data.get('appointmentDate')
        branch_code = request.data.get('branch_code')
        
        # Get branch_code from cookie if not in request data
        if not branch_code:
            branch_code = request.COOKIES.get('branch_code')
        
        # Check if branch_code is valid (this is just an example validation)
        if not branch_code:
            return Response({"error": "Branch code is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(patientUID=patient_uid)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        except Patient.MultipleObjectsReturned:
            return Response({"error": "Multiple patients found"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the patient already has an appointment on the given date in the same branch
        existing_appointment = Appointment.objects.filter(
            patientUID=patient_uid, 
            appointmentDate=appointment_date,
            branch_code=branch_code
        ).first()
        
        if existing_appointment:
            return Response({"error": f"Patient already has an appointment on {appointment_date}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add patient details and branch_code to the request data
        request.data['purposeOfVisit'] = patient.purposeOfVisit
        request.data['gender'] = patient.gender
        request.data['branch_code'] = branch_code
        
        # Serialize and save the new appointment
        serializer = AppointmentSerializer(data=request.data)
        if serializer.is_valid():
            appointment = serializer.save()
            
            # Set the branch_code in the response cookie as well
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            response.set_cookie('branch_code', branch_code, max_age=7*24*60*60)  # 7 days
            
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

  
@api_view(['GET'])
def AppointmentView(request):
    if request.method == 'GET':
        # Get branch_code from request parameters or cookies
        branch_code = request.query_params.get('branch_code') or request.COOKIES.get('branch_code')
        
        # If branch code is provided, filter by it
        if branch_code:
            data = Appointment.objects.filter(branch_code=branch_code)
        else:
            # Optional: Return error if no branch code is provided
            # return Response({"error": "Branch code is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Or return all appointments if no branch code filtering is needed
            data = Appointment.objects.all()
            
        serializer = AppointmentSerializer(data, many=True)
        return Response(serializer.data)
    


@api_view(['POST', 'GET', 'PATCH'])
def SummaryDetailCreate(request):
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client['cosmetology']
    collection = db['cosmetology_summarydetail']
    
    # Get branch_code from request or cookies
    branch_code = request.data.get('branch_code') or request.query_params.get('branch_code') or request.COOKIES.get('branch_code')
    
    if request.method == 'POST':
        try:
            # Add branch_code to request data if not present
            if not request.data.get('branch_code') and branch_code:
                request.data['branch_code'] = branch_code
                
            serializer = SummaryDetailSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        try:
            date_str = request.GET.get('appointmentDate')
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Query SummaryDetail objects based on date and branch_code if provided
            if branch_code:
                summaries = SummaryDetail.objects.filter(appointmentDate=date, branch_code=branch_code)
            else:
                summaries = SummaryDetail.objects.filter(appointmentDate=date)
            
            # Serialize the queryset
            serializer = SummaryDetailSerializer(summaries, many=True)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


    elif request.method == 'PATCH':
        try:
            date_str = request.data.get('appointmentDate')
            patientUID = request.data.get('patientUID')

            # Validate required fields
            if not date_str or not patientUID:
                return Response({'error': 'Both appointmentDate and patientUID are required'}, status=status.HTTP_400_BAD_REQUEST)

            date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Query to find the existing document, including branch_code if provided
            query = {"appointmentDate": str(date), "patientUID": patientUID}
            if branch_code:
                query["branch_code"] = branch_code
                
            existing_document = collection.find_one(query)

            if not existing_document:
                return Response({'error': 'No matching summary data found'}, status=status.HTTP_404_NOT_FOUND)

            # Merge existing data with new data
            updated_data = {**existing_document, **request.data}
            
            # Ensure branch_code is preserved
            if not updated_data.get('branch_code') and branch_code:
                updated_data['branch_code'] = branch_code

            # Safely append data for string fields without redundant commas
            def append_field(existing_value, new_value):
                if existing_value and new_value:
                    # Only add a comma if there is a value in both the existing and new values
                    if existing_value.endswith(","):
                        return f"{existing_value.strip()}, {new_value.strip()}"
                    return f"{existing_value.strip()}, {new_value.strip()}"
                elif existing_value:
                    return existing_value.strip()  # return the existing value if new value is empty
                return new_value.strip() if new_value else ""  # return the new value if existing value is empty

            if "diagnosis" in request.data:
                updated_data["diagnosis"] = append_field(existing_document.get("diagnosis", ""), request.data["diagnosis"])

            if "findings" in request.data:
                updated_data["findings"] = append_field(existing_document.get("findings", ""), request.data["findings"])

            if "prescription" in request.data:
                updated_data["prescription"] = append_field(existing_document.get("prescription", ""), request.data["prescription"])

            if "tests" in request.data:
                updated_data["tests"] = append_field(existing_document.get("tests", ""), request.data["tests"])

            updated_data.pop('_id', None)  # Remove '_id' to avoid conflicts during update

            # Update the document
            collection.update_one(query, {"$set": updated_data})

            # Fetch the updated document
            updated_document = collection.find_one(query)
            updated_document['_id'] = str(updated_document['_id'])  # Convert ObjectId to string

            return Response(updated_document, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def PatientDetailsView(request):
    try:
        date_str = request.GET.get('appointmentDate')
        branch_code = request.query_params.get('branch_code') or request.COOKIES.get('branch_code')
        
        if date_str is None:
            return Response({'error': 'Date parameter is missing'}, status=status.HTTP_400_BAD_REQUEST)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Query SummaryDetail objects based on date and branch_code if provided
        if branch_code:
            summaries = SummaryDetail.objects.filter(appointmentDate=date, branch_code=branch_code)
        else:
            summaries = SummaryDetail.objects.filter(appointmentDate=date)
            
        # Serialize the queryset
        serializer = SummaryDetailSerializer(summaries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except ValueError:
        return Response({'error': 'Invalid date format. Expected YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_medicine_price(request):
    try:
        # Fetch query parameters
        medicine_name = request.GET.get('medicine_name')
        batch_number = request.GET.get('batch_number')
        branch_code = request.query_params.get('branch_code') or request.COOKIES.get('branch_code')

        # Apply filters based on query parameters
        medicines = Pharmacy.objects.all()

        if medicine_name:
            medicines = medicines.filter(medicine_name__icontains=medicine_name)
        if batch_number:
            medicines = medicines.filter(batch_number=batch_number)
        if branch_code:
            medicines = medicines.filter(branch_code=branch_code)

        # Exclude medicines with old_stock equal to 0
        medicines = medicines.filter(old_stock__gt=0)

        # Check if any medicines exist after filtering
        if not medicines.exists():
            return Response({'message': 'No medicines found matching the criteria or stock is empty'}, status=status.HTTP_404_NOT_FOUND)

        # Get the medicine with the lowest old stock greater than 0
        lowest_stock_medicine = medicines.order_by('old_stock').first()

        # Serialize the response data
        response_data = {
            'medicine_name': lowest_stock_medicine.medicine_name,
            'company_name': lowest_stock_medicine.company_name,
            'price': str(Decimal(lowest_stock_medicine.price)),
            'CGST_percentage': lowest_stock_medicine.CGST_percentage,
            'CGST_value': lowest_stock_medicine.CGST_value,
            'SGST_percentage': lowest_stock_medicine.SGST_percentage,
            'SGST_value': lowest_stock_medicine.SGST_value,
            'new_stock': lowest_stock_medicine.new_stock,
            'old_stock': lowest_stock_medicine.old_stock,
            'received_date': lowest_stock_medicine.received_date,
            'expiry_date': lowest_stock_medicine.expiry_date,
            'batch_number': lowest_stock_medicine.batch_number,
            'branch_code': lowest_stock_medicine.branch_code,
        }

        # Return response
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@csrf_exempt
def check_upcoming_visits(request):
    branch_code = request.query_params.get('branch_code') or request.COOKIES.get('branch_code')
    
    one_week_from_now = timezone.now().date() + timedelta(days=7)
    
    # Filter by branch_code if provided
    if branch_code:
        upcoming_visits = SummaryDetail.objects.filter(branch_code=branch_code)
    else:
        upcoming_visits = SummaryDetail.objects.all()
        
    filtered_visits = []

    for visit in upcoming_visits:
        if visit.nextVisit:  # Ensure nextVisit is not None
            try:
                # Parse the next visit date
                next_visit_date = datetime.strptime(visit.nextVisit, '%d/%m/%Y').date()
                if timezone.now().date() <= next_visit_date <= one_week_from_now:
                    filtered_visits.append({
                        'patientUID': visit.patientUID,
                        'patientName': visit.patientName,
                        'nextVisit': visit.nextVisit,
                        'branch_code': visit.branch_code
                    })
            except ValueError:
                continue  # Skip if the date format is invalid

    data = {
        'upcoming_visits': filtered_visits
    }

    return JsonResponse(data)



# Modified vitalform to support branch_code
@api_view(['POST', 'GET'])
@csrf_exempt
def vitalform(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        branch_code = data.get('branch_code') or request.COOKIES.get('branch_code')
        
        # Validate branch_code
        if not branch_code:
            return Response({'status': 'error', 'message': 'Branch code is required'}, status=400)
            
        vital = Vital.objects.create(
            patientUID=data.get('patientUID'),
            patientName=data.get('patientName'),
            mobileNumber=data.get('mobileNumber'),
            height=data.get('height'),
            weight=data.get('weight'),
            pulseRate=data.get('pulseRate'),
            bloodPressure=data.get('bloodPressure'),
            branch_code=branch_code
        )
        serializer = VitalSerializer(vital)
        response = Response({'status': 'success', 'vital': serializer.data})
        response.set_cookie('branch_code', branch_code, max_age=7*24*60*60)  # 7 days
        return response
    elif request.method == 'GET':
        patientUID = request.GET.get('patientUID')
        branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')
        
        # Filter by branch_code if provided
        if branch_code:
            vitals = Vital.objects.filter(patientUID=patientUID, branch_code=branch_code)
        else:
            vitals = Vital.objects.filter(patientUID=patientUID)
            
        serializer = VitalSerializer(vitals, many=True)
        return Response({'status': 'success', 'vital': serializer.data})
    


@api_view(['GET', 'POST'])
def diagnosis_list(request):
    if request.method == 'GET':
        # Fetch all diagnoses from the database
        diagnoses = Diagnosis.objects.all()
        serializer = DiagnosisSerializer(diagnoses, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Deserialize the data
        serializer = DiagnosisSerializer(data=request.data)
        if serializer.is_valid():
            # Save the new diagnosis to the database
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET', 'POST'])
def Complaints_list(request):
    if request.method == 'GET':
        # Fetch all diagnoses from the database
        complaints = Complaints.objects.all()
        serializer = ComplaintsSerializer(complaints, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Deserialize the data
        serializer = ComplaintsSerializer(data=request.data)
        if serializer.is_valid():
            # Save the new diagnosis to the database
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET', 'POST'])
def Findings_list(request):
    if request.method == 'GET':
        # Fetch all diagnoses from the database
        findings = Findings.objects.all()
        serializer = FindingsSerializer(findings, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Deserialize the data
        serializer = FindingsSerializer(data=request.data)
        if serializer.is_valid():
            # Save the new diagnosis to the database
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET', 'POST'])
def Tests_list(request):
    if request.method == 'GET':
        # Fetch all diagnoses from the database
        tests = Tests.objects.all()
        serializer = TestsSerializer(tests, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Deserialize the data
        serializer = TestsSerializer(data=request.data)
        if serializer.is_valid():
            # Save the new diagnosis to the database
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET', 'POST'])
def Procedure_list(request):
    if request.method == 'GET':
        # Fetch all diagnoses from the database
        procedure = Procedure.objects.all()
        serializer = ProcedureSerializer(procedure, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Deserialize the data
        serializer = ProcedureSerializer(data=request.data)
        if serializer.is_valid():
            # Save the new diagnosis to the database
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 


client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
db = client['cosmetology']
collection = db['cosmetology_billingdata']
@api_view(['POST'])
@csrf_exempt
def save_billing_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            patientUID = data.get('patientUID')
            patientName = data.get('patientName')
            patient_handledby = data.get('patient_handledby')
            date = data.get('appointmentDate')
            table_data = data.get('table_data')
            netAmount = data.get('netAmount')
            discount = data.get('discount')
            payment_type = data.get('paymentType')
            section = data.get('section')
            branch_code = data.get('branch_code') or request.COOKIES.get('branch_code')
            
            # Validate branch_code
            if not branch_code:
                return JsonResponse({'error': 'Branch code is required.'}, status=400)

            if not date:
                return JsonResponse({'error': 'Date is required.'}, status=400)
            
            # Validate table_data as a JSON object
            if isinstance(table_data, str):
                table_data = json.loads(table_data)

            # Generate the serial number based on payment type and section
            bill_number = generate_serial_number(payment_type, section)
            
            # Create a new BillingData entry
            billing_data = BillingData(
                patientUID=patientUID,
                patientName=patientName,
                appointmentDate=date,
                patient_handledby=patient_handledby,
                table_data=table_data,
                netAmount=netAmount,
                discount=discount,
                paymentType=payment_type,
                billNumber=bill_number,
                branch_code=branch_code
            )
            billing_data.save()

            response = JsonResponse({'success': 'Billing data successfully saved!', 'serialNumber': bill_number}, status=201)
            response.set_cookie('branch_code', branch_code, max_age=7*24*60*60)  # 7 days
            return response
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method.'}, status=405)


def generate_serial_number(payment_type, section):
    current_year = timezone.now().year  # Get the current year
    prefix = ''

    # Define prefixes based on payment type and section
    if payment_type == 'Cash':
        if section == 'Pharmacy':
            prefix = 'CPhar'
        elif section == 'Consumer':
            prefix = 'CCosu'
        elif section == 'Procedure':
            prefix = 'CProc'
    elif payment_type == 'Card':
        if section == 'Pharmacy':
            prefix = 'Phar'
        elif section == 'Consumer':
            prefix = 'Cosu'
        elif section == 'Procedure':
            prefix = 'Proc'

    # Filter by prefix and current year to find the highest bill number in both models
    last_bill_billingdata = BillingData.objects.filter(
        billNumber__startswith=f"{prefix}/{current_year}/"
    ).order_by('-billNumber').first()

    if section == 'Consumer':
        last_bill_procedurebill = ProcedureBill.objects.filter(
            consumerBillNumber__startswith=f"{prefix}/{current_year}/"
        ).order_by('-consumerBillNumber').first()
    elif section == 'Procedure':
        last_bill_procedurebill = ProcedureBill.objects.filter(
            procedureBillNumber__startswith=f"{prefix}/{current_year}/"
        ).order_by('-procedureBillNumber').first()
    else:
        last_bill_procedurebill = None  # Ensure no invalid query occurs

    # Determine the highest sequence number between the two models
    last_serial_billingdata = 0
    last_serial_procedurebill = 0

    if last_bill_billingdata:
        try:
            last_serial_billingdata = int(last_bill_billingdata.billNumber.split('/')[-1])
        except ValueError:
            last_serial_billingdata = 0

    if last_bill_procedurebill:
        try:
            if section == 'Consumer':
                last_serial_procedurebill = int(last_bill_procedurebill.consumerBillNumber.split('/')[-1])
            elif section == 'Procedure':
                last_serial_procedurebill = int(last_bill_procedurebill.procedureBillNumber.split('/')[-1])
        except ValueError:
            last_serial_procedurebill = 0

    # Use the highest sequence number from both models
    new_sequence = max(last_serial_billingdata, last_serial_procedurebill) + 1

    # Format the serial number as per the desired pattern
    bill_number = f"{prefix}/{current_year}/{new_sequence:03d}"
    return bill_number


@api_view(['GET'])
def summary_get(request):
    if request.method == 'GET':
        try:
            # Get parameters from the request
            date_str = request.GET.get('appointmentDate')
            patientUID = request.GET.get('patientUID')
            branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')
            
            # Validate parameters
            if not date_str or not patientUID:
                return Response({'error': 'Both appointmentDate and patientUID are required'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Convert date string to date object
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Filter records based on parameters
            if branch_code:
                summaries = SummaryDetail.objects.filter(appointmentDate=date, patientUID=patientUID, branch_code=branch_code)
            else:
                summaries = SummaryDetail.objects.filter(appointmentDate=date, patientUID=patientUID)
                
            # Serialize and return the data
            serializer = SummaryDetailSerializer(summaries, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Update update_billing_data to use branch_code
@api_view(['PUT'])
@csrf_exempt
def update_billing_data(request):
    try:
        patientUID = request.data.get('patientUID')
        date = request.data.get('appointmentDate')
        table_data = request.data.get('table_data')
        branch_code = request.data.get('branch_code') or request.COOKIES.get('branch_code')

        if not patientUID or not date or not table_data:
            return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate table_data as a JSON object
        if isinstance(table_data, str):
            table_data = json.loads(table_data)

        # Find and update the record with branch_code if provided
        query = {'patientUID': patientUID, 'appointmentDate': date}
        if branch_code:
            query['branch_code'] = branch_code

        result = collection.find_one_and_update(
            query,
            {'$set': {'table_data': table_data}},  # Update table_data with JSON object
            return_document=True
        )

        if result:
            return Response({'message': 'Data updated successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Data not found'}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Update delete_billing_data to use branch_code
@require_http_methods(["DELETE"])
@csrf_exempt
def delete_billing_data(request):
    logger.info(f"Request method: {request.method}")
    if request.method == 'DELETE':
        try:
            # Parse request body
            data = json.loads(request.body.decode('utf-8'))
            patient_uid = data.get('patientUID')  # Patient UID
            bill_number = data.get('billNumber')  # Bill Number
            branch_code = data.get('branch_code') or request.COOKIES.get('branch_code')

            # Validate input data
            if not patient_uid or not bill_number:
                return JsonResponse({'message': 'Missing patientUID or billNumber'}, status=400)

            # Delete the specific record using patientUID and billNumber
            query = {'patientUID': patient_uid, 'billNumber': bill_number}
            if branch_code:
                query['branch_code'] = branch_code

            deleted_count, _ = BillingData.objects.filter(**query).delete()

            if deleted_count > 0:
                return JsonResponse({'message': 'Data deleted successfully'}, status=200)
            else:
                return JsonResponse({'message': 'No matching record found'}, status=404)
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return JsonResponse({'message': str(e)}, status=400)
    return JsonResponse({'message': 'Method not allowed'}, status=405)



# Update delete_procedure_data to use branch_code
@require_http_methods(["DELETE"])
@csrf_exempt
def delete_procedure_data(request):
    logger.info(f"Request method: {request.method}")
    if request.method == 'DELETE':
        try:
            # Log the raw body
            logger.info(f"Raw request body: {request.body}")

            # Parse request body
            data = json.loads(request.body.decode('utf-8'))
            logger.info(f"Parsed request data: {data}")

            patient_uid = data.get('patientUID')  # Patient UID
            consumer_bill_number = data.get('consumerBillNumber')  # Consumer Bill Number
            procedure_bill_number = data.get('procedureBillNumber')  # Procedure Bill Number
            branch_code = data.get('branch_code') or request.COOKIES.get('branch_code')

            # Validate input data
            if not patient_uid:
                return JsonResponse({'message': 'Missing patientUID'}, status=400)
            
            if not consumer_bill_number and not procedure_bill_number:
                return JsonResponse({'message': 'Either consumerBillNumber or procedureBillNumber must be provided'}, status=400)

            # Build query for deletion
            query = {'patientUID': patient_uid}

            if consumer_bill_number:
                query['consumerBillNumber'] = consumer_bill_number
            
            if procedure_bill_number:
                query['procedureBillNumber'] = procedure_bill_number
                
            if branch_code:
                query['branch_code'] = branch_code

            # Log the query
            logger.info(f"Query for deletion: {query}")

            # Perform deletion
            deleted_count, _ = ProcedureBill.objects.filter(**query).delete()

            if deleted_count > 0:
                return JsonResponse({'message': 'Data deleted successfully'}, status=200)
            else:
                return JsonResponse({'message': 'No matching record found'}, status=404)
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return JsonResponse({'message': str(e)}, status=400)
    return JsonResponse({'message': 'Method not allowed'}, status=405)


# Update get_summary_by_interval to use branch_code
@api_view(['GET'])
@csrf_exempt
def get_summary_by_interval(request, interval):
    date_str = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter is missing'}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if interval == 'day':
        start_date = selected_date
        end_date = selected_date
    elif interval == 'month':
        start_date = selected_date.replace(day=1)
        # Determine the end of the month
        next_month = (start_date + timedelta(days=31)).replace(day=1)
        end_date = next_month - timedelta(days=1)
    else:
        return JsonResponse({'error': 'Invalid interval'}, status=400)

    # Filter with branch_code if available
    if branch_code:
        summaries = SummaryDetail.objects.filter(
            appointmentDate__range=(start_date, end_date),
            branch_code=branch_code
        )
    else:
        summaries = SummaryDetail.objects.filter(
            appointmentDate__range=(start_date, end_date)
        )
        
    serializer = SummaryDetailSerializer(summaries, many=True)
    return JsonResponse(serializer.data, safe=False)


# Update get_billing_by_interval to use branch_code
@api_view(['GET'])
def get_billing_by_interval(request, interval):
    date_str = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter is missing'}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if interval == 'day':
        start_date = selected_date
        end_date = selected_date  # Start and end on the same day
    elif interval == 'week':
        start_date = selected_date
        end_date = start_date + timedelta(days=6)
    elif interval == 'month':
        start_date = selected_date.replace(day=1)  # First day of the month
        # Calculate the last day of the month
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_month.replace(day=1) - timedelta(days=1)
    else:
        return JsonResponse({'error': 'Invalid interval'}, status=400)

    # Filter records with branch_code if available
    if branch_code:
        billing = BillingData.objects.filter(
            appointmentDate__gte=start_date, 
            appointmentDate__lte=end_date,
            branch_code=branch_code
        )
    else:
        billing = BillingData.objects.filter(
            appointmentDate__gte=start_date, 
            appointmentDate__lte=end_date
        )
        
    serializer = BillingDataSerializer(billing, many=True)
    return JsonResponse({'billing_data': serializer.data}, safe=False)


# Update get_procedurebilling_by_interval to use branch_code
@api_view(['GET'])
@csrf_exempt
def get_procedurebilling_by_interval(request, interval):
    date_str = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter is missing'}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if interval == 'day':
        start_date = selected_date
        end_date = selected_date  # Start and end on the same day
    elif interval == 'week':
        start_date = selected_date
        end_date = start_date + timedelta(days=6)
    elif interval == 'month':
        start_date = selected_date.replace(day=1)  # First day of the month
        # Calculate the last day of the month
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_month.replace(day=1) - timedelta(days=1)
    else:
        return JsonResponse({'error': 'Invalid interval'}, status=400)

    # Filter records with branch_code if available
    if branch_code:
        procedurebilling = ProcedureBill.objects.filter(
            appointmentDate__gte=start_date, 
            appointmentDate__lte=end_date,
            branch_code=branch_code
        )
    else:
        procedurebilling = ProcedureBill.objects.filter(
            appointmentDate__gte=start_date, 
            appointmentDate__lte=end_date
        )
        
    serializer = ProcedureBillSerializer(procedurebilling, many=True)
    return JsonResponse(serializer.data, safe=False)


# Update get_procedures_bill to use branch_code
@require_GET
def get_procedures_bill(request):
    date_str = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter is missing'}, status=400)
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Fetch all records for the given date with branch_code if available
        if branch_code:
            summary_details = SummaryDetail.objects.filter(
                appointmentDate=date,
                branch_code=branch_code
            )
        else:
            summary_details = SummaryDetail.objects.filter(appointmentDate=date)
            
        # Initialize a dictionary to hold detailed records by patient UID
        detailed_records = {}
        # Iterate over all matching records and aggregate their details
        for detail in summary_details:
            # Skip if proceduresList is empty or contains only whitespace
            if not detail.proceduresList.strip():
                continue

            procedures = detail.proceduresList.split('\n')
            patient_uid = detail.patientUID
            if patient_uid not in detailed_records:
                detailed_records[patient_uid] = {
                    'patientUID': patient_uid,
                    'patientName': detail.patientName,
                    'appointmentDate': detail.appointmentDate,
                    'patient_handledby':detail.patient_handledby,

                    'procedures': []
                }
            for procedure in procedures:
                if procedure.strip():  # Avoid adding empty strings
                    # Extract procedure details, assuming format "Procedure: <name> - Date: <date>"
                    parts = procedure.split(' - Date: ')
                    if len(parts) == 2:
                        procedure_name = parts[0].replace('Procedure: ', '').strip()
                        procedure_date = parts[1].strip()
                        detailed_records[patient_uid]['procedures'].append({
                            'procedure': procedure_name,
                            'procedureDate': procedure_date
                        })
        # Convert detailed_records to a list for JSON response
        response_data = list(detailed_records.values())
        # Return the detailed records
        return JsonResponse({'detailedRecords': response_data}, safe=False)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)


# Update post_procedures_bill to use branch_code
@api_view(['POST'])
def post_procedures_bill(request):
    try:
        data = json.loads(request.body)
        patientUID = data.get('patientUID')
        patientName = data.get('patientName')
        appointmentDate = data.get('appointmentDate')
        patient_handledby = data.get('patient_handledby')
        procedures = data.get('procedures')  # Ensure this is a valid JSON object
        procedureNetAmount = data.get('procedureNetAmount')
        consumerNetAmount = data.get('consumerNetAmount')
        consumer = data.get('consumer')  # Ensure this is a valid JSON object
        branch_code = data.get('branch_code') or request.COOKIES.get('branch_code')

        # Get payment types and sections for both bills
        payment_type = data.get('PaymentType')

        # Generate serial numbers for both consumer and procedure
        consumer_bill_number = generate_serial_number(payment_type, 'Consumer')
        procedure_bill_number = generate_serial_number(payment_type, 'Procedure')

        # Validate the JSON fields
        if isinstance(procedures, str):
            procedures = json.loads(procedures)
        if isinstance(consumer, str):
            consumer = json.loads(consumer)

        # Save the billing data
        billing_data = ProcedureBill(
            patientUID=patientUID,
            patientName=patientName,
            appointmentDate=appointmentDate,
            patient_handledby=patient_handledby,
            procedures=procedures,
            procedureNetAmount=procedureNetAmount,
            consumerNetAmount=consumerNetAmount,
            consumer=consumer,
            consumerBillNumber=consumer_bill_number,
            PaymentType=payment_type,
            procedureBillNumber=procedure_bill_number,
            branch_code=branch_code,  # Add branch_code
        )
        billing_data.save()

        return JsonResponse({'success': 'Billing data saved successfully!', 'consumerBillNumber': consumer_bill_number, 'procedureBillNumber': procedure_bill_number}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# Update medical_history to use branch_code
@csrf_exempt
def medical_history(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        patientUID = data.get('id')
        branch_code = data.get('branch_code') or request.COOKIES.get('branch_code')
        
        if not patientUID:
            return JsonResponse({'error': 'Patient UID not provided'}, status=400)
            
        # Filter with branch_code if available
        if branch_code:
            patient_details = SummaryDetail.objects.filter(
                patientUID=patientUID,
                branch_code=branch_code
            ).values()
        else:
            patient_details = SummaryDetail.objects.filter(patientUID=patientUID).values()
            
        return JsonResponse(list(patient_details), safe=False)
        


# Connect to MongoDB
client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
db = client['cosmetology']
fs = GridFS(db)

@csrf_exempt
def upload_file(request):
    if request.method == 'POST':
        patient_name = request.POST.get('patient_name')
        branch_code = request.POST.get('branch_code') or request.COOKIES.get('branch_code')
        
        if 'images' in request.FILES:
            imgsrc_files = request.FILES.getlist('images')
            uploaded_files = []
            
            for index, imgsrc_file in enumerate(imgsrc_files):
                # Add branch code to filename if available
                if branch_code:
                    imgsrc_filename = f'{branch_code}_{patient_name}_{index}.jpg'
                else:
                    imgsrc_filename = f'{patient_name}_{index}.jpg'
                
                # Store file in GridFS with additional metadata
                imgsrc_id = fs.put(
                    imgsrc_file, 
                    filename=imgsrc_filename,
                    patient_name=patient_name,
                    branch_code=branch_code
                )
                uploaded_files.append(imgsrc_filename)
                
            return HttpResponse(f'Images uploaded successfully: {", ".join(uploaded_files)}')
        return HttpResponseBadRequest('No image files provided')
    return HttpResponseBadRequest('Invalid request method')


@csrf_exempt
def get_file(request):
    """
    View to retrieve a file from MongoDB GridFS.
    This view handles GET requests to retrieve a file from MongoDB GridFS based on the provided filename.
    Args:
        request (HttpRequest): The HTTP request object containing the filename to retrieve.
    Returns:
        HttpResponse: An HTTP response containing the file contents or a 404 error if the file is not found.
    """
    # Connect to MongoDB
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client['cosmetology']
    fs = GridFS(db)
    
    # Get the filename and branch_code from the request parameters
    filename = request.GET.get('filename')
    branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')
    
    # Find the file in MongoDB GridFS
    # If branch_code is provided, try to find file with matching branch_code first
    file = None
    if branch_code:
        file = fs.find_one({"filename": filename, "branch_code": branch_code})
    
    # If not found with branch_code or branch_code not provided, try without branch filtering
    if file is None:
        file = fs.find_one({"filename": filename})
    
    if file is not None:
        # Return the file contents as an HTTP response
        response = HttpResponse(file.read())
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment; filename=%s' % file.filename
        return response
    else:
        # Return a 404 error if the file is not found
        return HttpResponse(status=404)

@csrf_exempt
def upload_pdf(request):
    if request.method == 'POST':
        patient_name = request.POST.get('patient_name')
        branch_code = request.POST.get('branch_code') or request.COOKIES.get('branch_code')
        
        if 'pdf_files' in request.FILES:
            pdf_files = request.FILES.getlist('pdf_files')
            uploaded_files = []
            
            for index, pdf_file in enumerate(pdf_files):
                # Add branch code to filename if available
                if branch_code:
                    pdf_filename = f'{branch_code}_{patient_name}_{index}.pdf'
                else:
                    pdf_filename = f'{patient_name}_{index}.pdf'
                
                # Store file in GridFS with additional metadata
                pdf_id = fs.put(
                    pdf_file, 
                    filename=pdf_filename,
                    patient_name=patient_name,
                    branch_code=branch_code
                )
                uploaded_files.append(pdf_filename)
                
            return HttpResponse(f'PDFs uploaded successfully: {", ".join(uploaded_files)}')
        return HttpResponseBadRequest('No PDF files provided')
    return HttpResponseBadRequest('Invalid request method')

@csrf_exempt
def get_pdf_file(request):
    """
    View to retrieve a PDF file from MongoDB GridFS.
    This view handles GET requests to retrieve a PDF file from MongoDB GridFS based on the provided filename.
    Args:
        request (HttpRequest): The HTTP request object containing the filename to retrieve.
    Returns:
        HttpResponse: An HTTP response containing the PDF file contents or a 404 error if the file is not found.
    """
    # Connect to MongoDB
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client['cosmetology']
    fs = GridFS(db)

    # Get the filename and branch_code from the request parameters
    filename = request.GET.get('filename')
    branch_code = request.GET.get('branch_code') or request.COOKIES.get('branch_code')
    
    # Find the file in MongoDB GridFS
    # If branch_code is provided, try to find file with matching branch_code first
    file = None
    if branch_code:
        file = fs.find_one({"filename": filename, "branch_code": branch_code})
    
    # If not found with branch_code or branch_code not provided, try without branch filtering
    if file is None:
        file = fs.find_one({"filename": filename})

    if file is not None:
        # Return the PDF file contents as an HTTP response
        response = HttpResponse(file.read())
        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = 'attachment; filename=%s' % file.filename
        return response
    else:
        # Return a 404 error if the PDF file is not found
        return HttpResponse(status=404)
