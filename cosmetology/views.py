from rest_framework.views import APIView
from gridfs import GridFS
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.utils import timezone
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo import MongoClient
from bson.objectid import ObjectId
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
import traceback

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

import os
from dotenv import load_dotenv

load_dotenv() 

from .serializers import RegisterSerializer
from django.db import DatabaseError

@csrf_exempt
@api_view(['GET', 'POST'])
def registration(request):
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except DatabaseError as e:
                print(traceback.format_exc())
                return Response({'error': 'Database error occurred.', 'details': str(e)}, status=500)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        users = Register.objects.all()
        serializer = RegisterSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

@api_view(['POST'])
@csrf_exempt
def login(request):
    if request.method == 'POST':
        username = request.data.get('username')
        password = request.data.get('password')
        endpoint = request.data.get('endpoint')

        if not username:
            return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not endpoint:
            return Response({'error': 'Endpoint is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Register.objects.get(id=username, password=password)
            
            # Extract branch code from the database
            branch_code = user.branch_code
            
            # Parse branch codes - handle both old string format and new object format
            branch_codes = []
            active_branches = []
            
            if isinstance(branch_code, str):
                # Handle old JSON string format
                try:
                    branch_codes_data = json.loads(branch_code)
                    if isinstance(branch_codes_data, list):
                        for item in branch_codes_data:
                            if isinstance(item, str):
                                branch_codes.append(item)
                                active_branches.append(item)  # Assume active for old format
                            elif isinstance(item, dict):
                                branch_codes.append(item['branch_code'])
                                if item.get('isactive', False):
                                    active_branches.append(item['branch_code'])
                except json.JSONDecodeError:
                    if branch_code.startswith('[') and branch_code.endswith(']'):
                        codes_str = branch_code[1:-1].replace('"', '').replace("'", "")
                        branch_codes = [code.strip() for code in codes_str.split(',')]
                        active_branches = branch_codes  # Assume all active for old format
                    else:
                        branch_codes = [branch_code]
                        active_branches = [branch_code]
            elif isinstance(branch_code, list):
                # New object format
                for item in branch_code:
                    if isinstance(item, dict):
                        branch_codes.append(item['branch_code'])
                        if item.get('isactive', False):
                            active_branches.append(item['branch_code'])
                    elif isinstance(item, str):
                        branch_codes.append(item)
                        active_branches.append(item)  # Assume active for string items
            else:
                branch_codes = []
                active_branches = []

            # Check endpoint restrictions
            if user.role != 'Admin':
                if endpoint == 'AdminLogin' and user.role != 'Admin':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)
                elif endpoint == 'PharmacistLogin' and user.role != 'Pharmacist':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)
                elif endpoint == 'ReceptionistLogin' and user.role != 'Receptionist':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)
                elif endpoint == 'DoctorLogin' and user.role != 'Doctor':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)
                elif endpoint == 'ManagerLogin' and user.role != 'Manager':
                    return Response('Access denied', status=status.HTTP_403_FORBIDDEN)

            # Create response data
            response_data = {
                'message': 'Login successful',
                'role': user.role,
                'id': user.id,
                'name': user.name, 
                'contact': user.contact,
                'branch_codes': active_branches,  # Only return active branches
                'all_branches': branch_codes,     # All branches for management
            }
            
            # Include single branch code for backward compatibility
            if len(active_branches) == 1:
                response_data['branch_code'] = active_branches[0]
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Register.DoesNotExist:
            return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)


# MongoDB connection setup (ensure this is outside the function or managed properly)
client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
db = client['cosmetology']
branch_collection = db['cosmetology_branch']
from .serializers import BranchStatusSerializer
@api_view(['POST'])
@csrf_exempt
def toggle_branch_status(request):
    """Toggle the active status of a branch for a user"""
    if request.method == 'POST':
        serializer = BranchStatusSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            branch_code = serializer.validated_data['branch_code']
            new_status = serializer.validated_data['isactive']
            
            try:
                user = Register.objects.get(id=user_id)
                
                # Update the branch status
                updated_branches = []
                branch_found = False
                
                for branch in user.branch_code:
                    if isinstance(branch, dict) and branch['branch_code'] == branch_code:
                        updated_branches.append({
                            'branch_code': branch_code,
                            'isactive': new_status
                        })
                        branch_found = True
                    else:
                        updated_branches.append(branch)
                
                if not branch_found:
                    return Response({'error': 'Branch not found for user'}, status=status.HTTP_404_NOT_FOUND)
                
                user.branch_code = updated_branches
                user.save()
                
                return Response({
                    'message': 'Branch status updated successfully',
                    'branch_code': branch_code,
                    'isactive': new_status
                }, status=status.HTTP_200_OK)
                
            except Register.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_user_branches(request, user_id):
    """Get all branches for a user with their active status"""
    if not user_id:
        return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        user = Register.objects.get(id=user_id)
        return Response({
            'user_id': user.id,
            'name': user.name,
            'branches': user.branch_code
        }, status=status.HTTP_200_OK)
    except Register.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@csrf_exempt
def toggle_branch_status(request):
    """Toggle the active status of a branch for a user, or add it if not present."""
    if request.method == 'POST':
        serializer = BranchStatusSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            branch_code = serializer.validated_data['branch_code']
            new_status = serializer.validated_data['isactive']

            try:
                user = Register.objects.get(id=user_id)

                updated_branches = []
                branch_found = False

                for branch_entry in user.branch_code: # Iterate through each branch dictionary
                    # Ensure branch_entry is a dictionary and has 'branch_code'
                    if isinstance(branch_entry, dict) and branch_entry.get('branch_code') == branch_code:
                        updated_branches.append({
                            'branch_code': branch_code,
                            'isactive': new_status
                        })
                        branch_found = True
                    else:
                        # Keep existing branches that are not the one being updated
                        updated_branches.append(branch_entry)

                if not branch_found:
                    # If branch_code was not found, it means it's a new assignment
                    updated_branches.append({
                        'branch_code': branch_code,
                        'isactive': new_status
                    })

                user.branch_code = updated_branches
                user.save()

                return Response({
                    'message': 'Branch status updated successfully',
                    'branch_code': branch_code,
                    'isactive': new_status
                }, status=status.HTTP_200_OK)

            except Register.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                # Log the full error for debugging in production
                print(f"Error in toggle_branch_status: {e}")
                return Response({'error': 'An internal server error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_user_branches(request, user_id):
    """Get all branches for a user with their active status"""
    if not user_id:
        return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = Register.objects.get(id=user_id)
        # Ensure 'name' is retrieved correctly from your Register model
        return Response({
            'user_id': user.id,
            'name': user.name, # Assuming your Register model has a 'name' field
            'branches': user.branch_code # This should be a list of dicts: [{'branch_code': 'B1', 'isactive': True}]
        }, status=status.HTTP_200_OK)
    except Register.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in get_user_branches: {e}")
        return Response({'error': 'An internal server error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_branches(request):
    try:
        # Directly fetch branches from MongoDB collection
        # Ensure your MongoDB documents have 'branch_code' and 'branch_name' fields
        branches = list(branch_collection.find({}, {'_id': 0, 'branch_code': 1, 'branch_name': 1}))
        
        # Convert MongoDB cursor to JSON compatible format
        # If branch_name is not present in some documents, handle it in frontend or here
        branches_json = json.loads(dumps(branches))
        
        return Response(branches_json, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error in get_branches: {e}")
        return Response({'error': 'An internal server error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

from bson import ObjectId

logger = logging.getLogger(__name__)

@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def pharmacy_data(request):
    branch_code = request.query_params.get('branch_code')

    if request.method in ['GET', 'POST', 'PUT', 'PATCH'] and not branch_code:
        logger.warning("Missing branch_code in request: 400 BAD REQUEST")
        return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)

    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client['cosmetology']
    pharmacy_collection = db.cosmetology_pharmacy

    if request.method == 'GET':
        try:
            query_filter = {}
            if branch_code:
                query_filter['branch_code'] = branch_code
            medicines = list(pharmacy_collection.find(query_filter))
            for medicine in medicines:
                medicine['_id'] = str(medicine['_id'])
                # Ensure stock field exists, default to 0 if not present
                if 'stock' not in medicine:
                    medicine['stock'] = 0
            logger.info("GET request successful: 200 OK")
            return Response(medicines, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"GET request failed: 500 ERROR - {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'POST':
        try:
            items_to_process = request.data if isinstance(request.data, list) else [request.data]
            inserted_ids, updated_count = [], 0
            for item in items_to_process:
                item = dict(item)
                item.pop('_id', None)
                if not item.get('branch_code') and branch_code:
                    item['branch_code'] = branch_code
                
                # Convert new_stock to stock for new entries
                if 'new_stock' in item:
                    item['stock'] = int(item.get('new_stock', 0))
                    item.pop('new_stock', None)
                
                # Remove old_stock and total_stock if present (legacy fields)
                item.pop('old_stock', None)
                item.pop('total_stock', None)
                
                # Ensure stock field exists
                if 'stock' not in item:
                    item['stock'] = 0
                
                existing_record = pharmacy_collection.find_one({
                    "medicine_name": item.get("medicine_name"),
                    "batch_number": item.get("batch_number"),
                    "branch_code": item.get("branch_code")
                })
                if existing_record:
                    # For existing records, add new stock to current stock
                    current_stock = existing_record.get('stock', 0)
                    item['stock'] = current_stock + item.get('stock', 0)
                    pharmacy_collection.update_one({"_id": existing_record["_id"]}, {"$set": item})
                    updated_count += 1
                else:
                    result = pharmacy_collection.insert_one(item)
                    inserted_ids.append(str(result.inserted_id))
            logger.info("POST request successful: 201 CREATED")
            return Response({
                "message": f"Processed {len(items_to_process)} records — {len(inserted_ids)} inserted, {updated_count} updated.",
                "inserted_ids": inserted_ids
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"POST request failed: 500 ERROR - {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'PATCH':
        try:
            request_data = request.data if isinstance(request.data, list) else [request.data]
            response_data = []
            for data in request_data:
                data = dict(data)
                _id = data.pop('_id', None)
                if not _id:
                    logger.warning("PATCH request missing _id: 400 BAD REQUEST")
                    return Response({"error": "_id is required for PATCH."}, status=status.HTTP_400_BAD_REQUEST)
                data['updated_at'] = datetime.now()
                if not data.get('branch_code') and branch_code:
                    data['branch_code'] = branch_code
                
                # Handle stock update logic
                if 'new_stock' in data and data['new_stock']:
                    existing_record = pharmacy_collection.find_one({"_id": ObjectId(_id)})
                    if existing_record:
                        current_stock = existing_record.get('stock', 0)
                        new_stock_value = int(data.get('new_stock', 0))
                        data['stock'] = current_stock + new_stock_value
                        # Remove new_stock from data as it's not stored in DB
                        data.pop('new_stock', None)
                
                # Remove legacy fields if present
                data.pop('old_stock', None)
                data.pop('total_stock', None)
                
                result = pharmacy_collection.update_one({"_id": ObjectId(_id)}, {"$set": data})
                if result.matched_count:
                    updated_doc = pharmacy_collection.find_one({"_id": ObjectId(_id)})
                    updated_doc['_id'] = str(updated_doc['_id'])
                    # Ensure stock field exists in response
                    if 'stock' not in updated_doc:
                        updated_doc['stock'] = 0
                    response_data.append(updated_doc)
                else:
                    logger.warning(f"PATCH _id not found: {_id} — 404 NOT FOUND")
                    return Response({'error': f'Document with _id {_id} not found'}, status=status.HTTP_404_NOT_FOUND)
            logger.info("PATCH request successful: 200 OK")
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"PATCH request failed: 500 ERROR - {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'PUT':
        try:
            request_data = request.data if isinstance(request.data, list) else [request.data]
            response_data = []
            for data in request_data:
                data = dict(data)
                _id = data.pop('_id', None)
                if not _id:
                    logger.warning("PUT request missing _id: 400 BAD REQUEST")
                    return Response({"error": "_id is required for PUT."}, status=status.HTTP_400_BAD_REQUEST)
                if not data.get('branch_code') and branch_code:
                    data['branch_code'] = branch_code
                data['updated_at'] = datetime.now()
                
                # Handle stock field for PUT requests
                if 'new_stock' in data:
                    data['stock'] = int(data.get('new_stock', 0))
                    data.pop('new_stock', None)
                
                # Remove legacy fields if present
                data.pop('old_stock', None)
                data.pop('total_stock', None)
                
                # Ensure stock field exists
                if 'stock' not in data:
                    data['stock'] = 0
                
                result = pharmacy_collection.update_one({"_id": ObjectId(_id)}, {"$set": data}, upsert=False)
                if result.matched_count:
                    updated_doc = pharmacy_collection.find_one({"_id": ObjectId(_id)})
                    updated_doc['_id'] = str(updated_doc['_id'])
                    # Ensure stock field exists in response
                    if 'stock' not in updated_doc:
                        updated_doc['stock'] = 0
                    response_data.append(updated_doc)
                else:
                    logger.warning(f"PUT _id not found: {_id} — 404 NOT FOUND")
                    return Response({'error': f'Document with _id {_id} not found'}, status=status.HTTP_404_NOT_FOUND)
            logger.info("PUT request successful: 200 OK")
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"PUT request failed: 500 ERROR - {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'DELETE':
        try:
            _id = request.query_params.get('_id')
            if not _id:
                logger.warning("DELETE request missing _id: 400 BAD REQUEST")
                return Response({'error': '_id is required for DELETE'}, status=status.HTTP_400_BAD_REQUEST)
            
            result = pharmacy_collection.delete_one({"_id": ObjectId(_id)})
            if result.deleted_count:
                logger.info(f"DELETE request successful: Record {_id} deleted")
                return Response({'message': 'Record deleted successfully'}, status=status.HTTP_200_OK)
            else:
                logger.warning(f"DELETE request: No record found with _id {_id}: 404 NOT FOUND")
                return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting pharmacy data: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# Setup MongoDB client
client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
db = client['cosmetology']
pharmacy_collection = db.cosmetology_pharmacy

@require_http_methods(["DELETE"])
@csrf_exempt
def delete_medicine(request, medicine_name):
    branch_code = request.GET.get('branch_code')
    
    if not branch_code:
        return JsonResponse({"error": "branch_code is required"}, status=400)
    if not medicine_name:
        return JsonResponse({"error": "medicine_name is required"}, status=400)

    query = {
        "medicine_name": medicine_name,
        "branch_code": branch_code
    }

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
        batch_number = data.get('batch_number')
        qty = data.get('qty')
        branch_code = data.get('branch_code')
        
        if not medicine_name:
            return Response({'error': 'medicine_name is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not batch_number:
            return Response({'error': 'batch_number is required'}, status=status.HTTP_400_BAD_REQUEST)
        if qty is None:
            return Response({'error': 'qty is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not branch_code:
            return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            qty = int(qty)
            client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
            db = client['cosmetology']
            pharmacy_collection = db.cosmetology_pharmacy

            query = {
                'medicine_name': medicine_name,
                'batch_number': batch_number,
                'branch_code': branch_code
            }

            document = pharmacy_collection.find_one(query)
            if not document:
                return Response({'error': 'Medicine not found'}, status=status.HTTP_404_NOT_FOUND)

            current_stock = document.get('stock', 0)
            new_stock = current_stock - qty

            if new_stock < 0:
                return Response({'error': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)

            result = pharmacy_collection.update_one(
                query,
                {'$set': {'stock': new_stock}}
            )

            if result.matched_count == 0:
                return Response({'error': 'Failed to update stock'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'message': 'Stock updated successfully'}, status=status.HTTP_200_OK)

        except ValueError:
            return Response({'error': 'Invalid quantity value'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def check_medicine_status(request):
    branch_code = request.query_params.get('branch_code')
    
    if not branch_code:
        return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    low_quantity_medicines = []
    near_expiry_medicines = []

    # Filter by branch_code
    medicines = Pharmacy.objects.filter(branch_code=branch_code)

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
    branch_code = request.data.get('branch_code')
    
    if not branch_code:
        return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if request.method == 'POST':
        # Add branch_code to request data
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
            # Find patient by UID and branch_code
            patient = Patient.objects.get(patientUID=patientUID, branch_code=branch_code)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Add branch_code to request data
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
            # Delete patient by UID and branch_code
            patient = Patient.objects.get(patientUID=patientUID, branch_code=branch_code)
            patient.delete()
            return Response({"message": "Patient deleted successfully"}, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def PatientView(request):
    if request.method == 'GET':
        branch_code = request.query_params.get('branch_code')
        
        if not branch_code:
            return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter by branch_code
        patients = Patient.objects.filter(branch_code=branch_code)
            
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)
    

@api_view(['POST'])
@csrf_exempt
def Appointmentpost(request):
    if request.method == 'POST':
        patient_uid = request.data.get('patientUID')
        appointment_date = request.data.get('appointmentDate')
        appointment_time = request.data.get('appointmentTime')
        branch_code = request.data.get('branch_code')
        
        # Validate required fields
        if not patient_uid:
            return Response({"error": "patientUID is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not appointment_date:
            return Response({"error": "appointmentDate is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not appointment_time:
            return Response({"error": "appointmentTime is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not branch_code:
            return Response({"error": "branch_code is required"}, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        # Check if the time slot is already booked by any patient on the same date and branch
        time_slot_booked = Appointment.objects.filter(
            appointmentDate=appointment_date,
            appointmentTime=appointment_time,
            branch_code=branch_code
        ).first()
        
        if time_slot_booked:
            return Response({"error": f"Time slot {appointment_time} is already booked for {appointment_date}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add patient details and branch_code to the request data
        request.data['purposeOfVisit'] = patient.purposeOfVisit
        request.data['gender'] = patient.gender
        request.data['branch_code'] = branch_code
        
        # Serialize and save the new appointment
        serializer = AppointmentSerializer(data=request.data)
        if serializer.is_valid():
            appointment = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
@csrf_exempt
@api_view(['GET'])
def get_doctors(request):
    """
    API endpoint to get users with role Doctor/Admin,
    filtered by branch_code (active only)
    """
    if request.method == 'GET':
        try:
            branch_code_filter = request.GET.get('branch_code')

            # Connect to MongoDB
            client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
            db = client['cosmetology']
            collection = db['cosmetology_register']

            # Fetch all doctors/admins
            all_users = collection.find({
                "role": {"$in": ["Doctor", "Admin"]}
            }, {
                "_id": 0,
                "id": 1,
                "name": 1,
                "role": 1,
                "branch_code": 1,
                "contact": 1
            })

            # Filter by branch_code if provided
            filtered_users = []
            for user in all_users:
                try:
                    branch_code_list = json.loads(user.get('branch_code', '[]'))
                except json.JSONDecodeError:
                    continue  # Skip invalid JSON

                if branch_code_filter:
                    for entry in branch_code_list:
                        if (
                            entry.get('branch_code') == branch_code_filter and
                            entry.get('isactive') == True
                        ):
                            filtered_users.append(user)
                            break  # No need to check further
                else:
                    filtered_users.append(user)

            return Response({
                "success": True,
                "doctors": filtered_users,
                "count": len(filtered_users)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "error": "Failed to fetch doctors and admins",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# Updated Appointment View to include doctor filtering
@api_view(['GET'])
def AppointmentView(request):
    if request.method == 'GET':
        branch_code = request.query_params.get('branch_code')
        doctor_name = request.query_params.get('doctor_name')  # optional
        role = request.query_params.get('role')  # either 'Admin' or 'Doctor'

        if not branch_code:
            return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Base query filtered by branch
        queryset = Appointment.objects.filter(branch_code=branch_code)

        # If role is Doctor, further filter by doctor_name
        if role == 'Doctor':
            if not doctor_name:
                return Response({'error': 'doctor_name is required for Doctor role'}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(patient_handledby__iexact=doctor_name.strip())

        serializer = AppointmentSerializer(queryset, many=True)
        return Response(serializer.data)
            

@api_view(['POST', 'GET', 'PATCH'])
def SummaryDetailCreate(request):
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client['cosmetology']
    collection = db['cosmetology_summarydetail']
    # Get branch_code from request
    branch_code = request.data.get('branch_code') or request.query_params.get('branch_code')
    
    if not branch_code:
        return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    if request.method == 'POST':
        try:
            # Add branch_code to request data
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
            
            if not date_str:
                return Response({'error': 'appointmentDate is required'}, status=status.HTTP_400_BAD_REQUEST)
                
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            # Query SummaryDetail objects based on date and branch_code
            summaries = SummaryDetail.objects.filter(appointmentDate=date, branch_code=branch_code)
            # Serialize the queryset
            serializer = SummaryDetailSerializer(summaries, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    elif request.method == 'PATCH':
        try:
            date_str = request.data.get('appointmentDate')
            patientUID = request.data.get('patientUID')
            # Validate required fields
            if not date_str:
                return Response({'error': 'appointmentDate is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not patientUID:
                return Response({'error': 'patientUID is required'}, status=status.HTTP_400_BAD_REQUEST)
                
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            # Query to find the existing document, including branch_code
            query = {"appointmentDate": str(date), "patientUID": patientUID, "branch_code": branch_code}
            existing_document = collection.find_one(query)
            if not existing_document:
                return Response({'error': 'No matching summary data found'}, status=status.HTTP_404_NOT_FOUND)
            # Create updated data starting with existing document
            updated_data = existing_document.copy()
            # Ensure branch_code is preserved
            updated_data['branch_code'] = branch_code
            # Handle prescription field - replace instead of append
            if "prescription" in request.data:
                # Directly replace the prescription field with new data
                updated_data["prescription"] = request.data["prescription"]
            # Handle other fields with append logic
            def append_field(existing_value, new_value):
                if not new_value or new_value.strip() == "":
                    return existing_value or ""
                if not existing_value or existing_value.strip() == "":
                    return new_value.strip()
                # Clean existing value and new value
                existing_clean = existing_value.strip()
                new_clean = new_value.strip()
                # Check if new value already exists in existing value
                if new_clean in existing_clean:
                    return existing_clean
                # Add comma if existing doesn't end with comma
                if existing_clean.endswith(","):
                    return f"{existing_clean} {new_clean}"
                else:
                    return f"{existing_clean}, {new_clean}"
            # Apply append logic to other fields
            if "diagnosis" in request.data:
                updated_data["diagnosis"] = append_field(
                    existing_document.get("diagnosis", ""),
                    request.data["diagnosis"]
                )
            if "findings" in request.data:
                updated_data["findings"] = append_field(
                    existing_document.get("findings", ""),
                    request.data["findings"]
                )
            if "tests" in request.data:
                updated_data["tests"] = append_field(
                    existing_document.get("tests", ""),
                    request.data["tests"]
                )
            # Handle other fields that should be directly updated (not appended)
            direct_update_fields = [
                'complaints', 'plans', 'nextVisit', 'vital', 'proceduresList',
                'patient_handledby', 'patientName', 'mobileNumber'
            ]
            for field in direct_update_fields:
                if field in request.data:
                    updated_data[field] = request.data[field]
            # Remove '_id' to avoid conflicts during update
            updated_data.pop('_id', None)
            # Update the document
            collection.update_one(query, {"$set": updated_data})
            # Fetch the updated document
            updated_document = collection.find_one(query)
            if updated_document and '_id' in updated_document:
                updated_document['_id'] = str(updated_document['_id'])  # Convert ObjectId to string
            return Response(updated_document, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_medicine_price(request):
    try:
        # Fetch query parameters
        medicine_name = request.GET.get('medicine_name')
        batch_number = request.GET.get('batch_number')
        branch_code = request.GET.get('branch_code')

        # Ensure branch_code is provided
        if not branch_code:
            return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Filter the queryset
        medicines = Pharmacy.objects.filter(branch_code=branch_code)

        if medicine_name:
            medicines = medicines.filter(medicine_name__iexact=medicine_name)
        if batch_number:
            medicines = medicines.filter(batch_number=batch_number)

        if not medicines.exists():
            return Response({'message': 'No medicines found matching the criteria'}, status=status.HTTP_404_NOT_FOUND)

        # Build response list
        response_data = []
        for med in medicines:
            response_data.append({
                'medicine_name': med.medicine_name,
                'company_name': med.company_name,
                'price': str(Decimal(med.price) if med.price is not None else Decimal('0.00')),
                'CGST_percentage': med.CGST_percentage,
                'CGST_value': float(med.CGST_value) if med.CGST_value is not None else 0.0,
                'SGST_percentage': med.SGST_percentage,
                'SGST_value': float(med.SGST_value) if med.SGST_value is not None else 0.0,
                'stock': getattr(med, 'stock', 0),
                'received_date': med.received_date,
                'expiry_date': med.expiry_date,
                'batch_number': med.batch_number,
                'branch_code': med.branch_code,
            })

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

from django.db.models import Q
@api_view(['GET'])
def get_patientbilling_data(request):
    """
    Unified endpoint to fetch billing data, with fallback to summary details
    """
    try:
        # Extract query params
        patientUID = request.GET.get('patientUID')
        appointmentDate = request.GET.get('appointmentDate')
        branch_code = request.GET.get('branch_code')

        # Validate mandatory fields
        if not appointmentDate:
            return Response({'error': 'appointmentDate is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not branch_code:
            return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Parse date
        try:
            date_obj = datetime.strptime(appointmentDate, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Expected YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        # Prepare base query
        base_query = Q(appointmentDate=appointmentDate, branch_code=branch_code)

        if patientUID:
            base_query &= Q(patientUID=patientUID)
            # Try billing data for patient
            billing = BillingData.objects.filter(base_query).last()
            if billing:
                serializer = BillingDataSerializer(billing)
                return Response({'source': 'billing', 'data': serializer.data}, status=status.HTTP_200_OK)

            # Fallback to summary detail
            summary = SummaryDetail.objects.filter(base_query).last()
            if summary:
                serializer = SummaryDetailSerializer(summary)
                return Response({'source': 'summary', 'data': serializer.data}, status=status.HTTP_200_OK)

            return Response({'message': 'No data found for this patient'}, status=status.HTTP_204_NO_CONTENT)

        else:
            # Try billing data for date + branch
            billings = BillingData.objects.filter(base_query).exclude(patient_handledby="N/A").order_by('-appointmentDate')
            if billings.exists():
                serializer = BillingDataSerializer(billings, many=True)
                return Response({'source': 'billing', 'data': serializer.data}, status=status.HTTP_200_OK)

            # Fallback to summary
            summaries = SummaryDetail.objects.filter(appointmentDate=date_obj, branch_code=branch_code)
            if summaries.exists():
                serializer = SummaryDetailSerializer(summaries, many=True)
                return Response({'source': 'summary', 'data': serializer.data}, status=status.HTTP_200_OK)

            return Response({'message': 'No data found for this date', 'data': []}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_patient_data: {str(e)}")
        return Response({'error': f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_patient_procedurebill_data(request):
    try:
        # Get parameters
        patientUID = request.GET.get('patientUID')
        appointmentDate = request.GET.get('appointmentDate')
        branch_code = request.GET.get('branch_code')

        # Validate required parameters
        if not appointmentDate or not branch_code:
            return Response({
                "error": "appointmentDate and branch_code are required parameters"
            }, status=status.HTTP_400_BAD_REQUEST)

        base_query = Q(appointmentDate=appointmentDate, branch_code=branch_code)

        # ─── Step 1: Try fetching from ProcedureBill ─────────────────────────────────
        if patientUID:
            base_query &= Q(patientUID=patientUID)
            procedure_bill = ProcedureBill.objects.filter(base_query).last()
            if procedure_bill:
                serializer = ProcedureBillSerializer(procedure_bill)
                return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            procedure_bills = ProcedureBill.objects.filter(base_query).exclude(patient_handledby="N/A").order_by('-appointmentDate')
            if procedure_bills.exists():
                serializer = ProcedureBillSerializer(procedure_bills, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

        # ─── Step 2: Fall back to SummaryDetail if no ProcedureBill data ──────────────
        try:
            date = datetime.strptime(appointmentDate, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Expected YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        summary_query = SummaryDetail.objects.filter(
            appointmentDate=date,
            branch_code=branch_code
        )

        if patientUID:
            summary_query = summary_query.filter(patientUID=patientUID)

        detailed_records = {}
        for detail in summary_query:
            if not detail.proceduresList.strip():
                continue

            procedures = detail.proceduresList.split('\n')
            uid = detail.patientUID
            if uid not in detailed_records:
                detailed_records[uid] = {
                    'patientUID': uid,
                    'patientName': detail.patientName,
                    'appointmentDate': detail.appointmentDate,
                    'patient_handledby': detail.patient_handledby,
                    'procedures': []
                }
            for procedure in procedures:
                if procedure.strip():
                    parts = procedure.split(' - Date: ')
                    if len(parts) == 2:
                        name = parts[0].replace('Procedure: ', '').strip()
                        proc_date = parts[1].strip()
                        detailed_records[uid]['procedures'].append({
                            'procedure': name,
                            'procedureDate': proc_date
                        })

        # Return fallback summary data
        response_data = list(detailed_records.values())
        if response_data:
            return Response({'detailedRecords': response_data}, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": "No procedure billing or summary data found",
                "data": []
            }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_procedure_bill_or_summary: {str(e)}")
        return Response({
            "error": f"Internal server error: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@require_GET
def getnewbill(request):
    patient_uid = request.GET.get('patientUID')
    appointment_date = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code')

    if not patient_uid or not appointment_date or not branch_code:
        return JsonResponse({'error': 'patientUID, appointmentDate, and branch_code are required'}, status=400)

    try:
        bills = BillingData.objects.filter(
            patientUID=patient_uid,
            appointmentDate=appointment_date,
            branch_code=branch_code,
            patient_handledby="N/A"
        )

        bill_data = []
        for bill in bills:
            bill_data.append({
                'patientUID': bill.patientUID,
                'patientName': bill.patientName,
                'appointmentDate': bill.appointmentDate,
                'branch_code': bill.branch_code,
                'netAmount': bill.netAmount,
                'discount': bill.discount,
                'paymentType': bill.paymentType,
                'billNumber': bill.billNumber,
                'table_data': bill.table_data,
                'patient_handledby': bill.patient_handledby,
            })

        return JsonResponse({'billingData': bill_data}, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def getnewprocedurebill(request):
    patient_uid = request.GET.get('patientUID')
    appointment_date = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code')

    if not patient_uid or not appointment_date or not branch_code:
        return JsonResponse({'error': 'patientUID, appointmentDate, and branch_code are required'}, status=400)

    try:
        procedure_bills = ProcedureBill.objects.filter(
            patientUID=patient_uid,
            appointmentDate=appointment_date,
            branch_code=branch_code,
            patient_handledby="N/A"
        )

        procedure_data = []
        for bill in procedure_bills:
            procedure_data.append({
                'patientUID': bill.patientUID,
                'patientName': bill.patientName,
                'appointmentDate': bill.appointmentDate,
                'branch_code': bill.branch_code,
                'procedures': bill.procedures,
                'procedureNetAmount': bill.procedureNetAmount,
                'consumerNetAmount': bill.consumerNetAmount,
                'consumer': bill.consumer,
                'paymentType': bill.PaymentType,
                'consumerBillNumber': bill.consumerBillNumber,
                'procedureBillNumber': bill.procedureBillNumber,
                'patient_handledby': bill.patient_handledby,
            })

        return JsonResponse({'procedureBillingData': procedure_data}, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@csrf_exempt
def check_upcoming_visits(request):
    branch_code = request.query_params.get('branch_code')
    
    if not branch_code:
        return JsonResponse({'error': 'branch_code is required'}, status=400)
    
    one_week_from_now = timezone.now().date() + timedelta(days=7)
    
    # Filter by branch_code
    upcoming_visits = SummaryDetail.objects.filter(branch_code=branch_code)
        
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


@api_view(['POST', 'GET'])
@csrf_exempt
def vitalform(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        branch_code = data.get('branch_code')
        
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
        return Response({'status': 'success', 'vital': serializer.data})
    elif request.method == 'GET':
        patientUID = request.GET.get('patientUID')
        branch_code = request.GET.get('branch_code')
        
        if not patientUID:
            return Response({'status': 'error', 'message': 'patientUID is required'}, status=400)
        if not branch_code:
            return Response({'status': 'error', 'message': 'branch_code is required'}, status=400)
        
        # Filter by branch_code
        vitals = Vital.objects.filter(patientUID=patientUID, branch_code=branch_code)
            
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
            branch_code = data.get('branch_code')
            
            # Validate required fields
            if not patientUID:
                return JsonResponse({'error': 'patientUID is required'}, status=400)
            if not patientName:
                return JsonResponse({'error': 'patientName is required'}, status=400)
            if not date:
                return JsonResponse({'error': 'appointmentDate is required'}, status=400)
            if not branch_code:
                return JsonResponse({'error': 'branch_code is required'}, status=400)
            if not payment_type:
                return JsonResponse({'error': 'paymentType is required'}, status=400)
            if not section:
                return JsonResponse({'error': 'section is required'}, status=400)
            
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

            return JsonResponse({'success': 'Billing data successfully saved!', 'serialNumber': bill_number}, status=201)
            
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
            branch_code = request.GET.get('branch_code')
            
            # Validate parameters
            if not date_str:
                return Response({'error': 'appointmentDate is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not patientUID:
                return Response({'error': 'patientUID is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not branch_code:
                return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Convert date string to date object
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Filter records based on parameters
            summaries = SummaryDetail.objects.filter(appointmentDate=date, patientUID=patientUID, branch_code=branch_code)
                
            # Serialize and return the data
            serializer = SummaryDetailSerializer(summaries, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@csrf_exempt
def update_billing_data(request):
    try:
        patientUID = request.data.get('patientUID')
        date = request.data.get('appointmentDate')
        table_data = request.data.get('table_data')
        branch_code = request.data.get('branch_code')

        if not patientUID:
            return Response({'error': 'patientUID is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not date:
            return Response({'error': 'appointmentDate is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not table_data:
            return Response({'error': 'table_data is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not branch_code:
            return Response({'error': 'branch_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate table_data as a JSON object
        if isinstance(table_data, str):
            table_data = json.loads(table_data)

        # Find and update the record with branch_code
        query = {
            'patientUID': patientUID, 
            'appointmentDate': date,
            'branch_code': branch_code
        }

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
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            branch_code = data.get('branch_code')

            # Validate input data
            if not patient_uid:
                return JsonResponse({'message': 'patientUID is required'}, status=400)
            if not bill_number:
                return JsonResponse({'message': 'billNumber is required'}, status=400)
            if not branch_code:
                return JsonResponse({'message': 'branch_code is required'}, status=400)

            # Delete the specific record using patientUID and billNumber
            query = {
                'patientUID': patient_uid, 
                'billNumber': bill_number,
                'branch_code': branch_code
            }

            deleted_count, _ = BillingData.objects.filter(**query).delete()

            if deleted_count > 0:
                return JsonResponse({'message': 'Data deleted successfully'}, status=200)
            else:
                return JsonResponse({'message': 'No matching record found'}, status=404)
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return JsonResponse({'message': str(e)}, status=400)
    return JsonResponse({'message': 'Method not allowed'}, status=405)


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
            branch_code = data.get('branch_code')

            # Validate input data
            if not patient_uid:
                return JsonResponse({'message': 'patientUID is required'}, status=400)
            if not branch_code:
                return JsonResponse({'message': 'branch_code is required'}, status=400)
            if not consumer_bill_number and not procedure_bill_number:
                return JsonResponse({'message': 'Either consumerBillNumber or procedureBillNumber must be provided'}, status=400)

            # Build query for deletion
            query = {
                'patientUID': patient_uid,
                'branch_code': branch_code
            }

            if consumer_bill_number:
                query['consumerBillNumber'] = consumer_bill_number
            
            if procedure_bill_number:
                query['procedureBillNumber'] = procedure_bill_number

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


@api_view(['GET'])
@csrf_exempt
def get_summary_by_interval(request, interval):    
    date_str = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code')
    
    if not date_str:
        return JsonResponse({'error': 'appointmentDate is required'}, status=400)
    if not branch_code:
        return JsonResponse({'error': 'branch_code is required'}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if interval == 'day':
        start_date = selected_date
        end_date = selected_date  # Start and end on the same day
    elif interval == 'month':
        start_date = selected_date.replace(day=1)  # First day of the month
        # Calculate the last day of the month
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_month.replace(day=1) - timedelta(days=1)
    else:
        return JsonResponse({'error': 'Invalid interval'}, status=400)

    # Filter records with branch_code
    summary = SummaryDetail.objects.filter(
        appointmentDate__gte=start_date, 
        appointmentDate__lte=end_date,
        branch_code=branch_code
    )
        
    serializer = SummaryDetailSerializer(summary, many=True)
    return JsonResponse({'summary_data': serializer.data}, safe=False)


@api_view(['GET'])
def get_billing_by_interval(request, interval):
    date_str = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code')
    
    if not date_str:
        return JsonResponse({'error': 'appointmentDate is required'}, status=400)
    if not branch_code:
        return JsonResponse({'error': 'branch_code is required'}, status=400)

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

    # Filter records with branch_code
    billing = BillingData.objects.filter(
        appointmentDate__gte=start_date, 
        appointmentDate__lte=end_date,
        branch_code=branch_code
    )
        
    serializer = BillingDataSerializer(billing, many=True)
    return JsonResponse({'billing_data': serializer.data}, safe=False)


@api_view(['GET'])
@csrf_exempt
def get_procedurebilling_by_interval(request, interval):
    date_str = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code')
    
    if not date_str:
        return JsonResponse({'error': 'appointmentDate is required'}, status=400)
    if not branch_code:
        return JsonResponse({'error': 'branch_code is required'}, status=400)

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

    # Filter records with branch_code
    procedurebilling = ProcedureBill.objects.filter(
        appointmentDate__gte=start_date, 
        appointmentDate__lte=end_date,
        branch_code=branch_code
    )
        
    serializer = ProcedureBillSerializer(procedurebilling, many=True)
    return JsonResponse(serializer.data, safe=False)


@require_GET
def get_procedures_bill(request):
    date_str = request.GET.get('appointmentDate')
    branch_code = request.GET.get('branch_code')
    
    if not date_str:
        return JsonResponse({'error': 'appointmentDate is required'}, status=400)
    if not branch_code:
        return JsonResponse({'error': 'branch_code is required'}, status=400)
        
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Fetch all records for the given date with branch_code
        summary_details = SummaryDetail.objects.filter(
            appointmentDate=date,
            branch_code=branch_code
        )
            
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
        branch_code = data.get('branch_code')
        payment_type = data.get('PaymentType')
        consultationFee = data.get('consultationFee')
        # Validate required fields
        if not patientUID:
            return JsonResponse({'error': 'patientUID is required'}, status=400)
        if not patientName:
            return JsonResponse({'error': 'patientName is required'}, status=400)
        if not appointmentDate:
            return JsonResponse({'error': 'appointmentDate is required'}, status=400)
        if not branch_code:
            return JsonResponse({'error': 'branch_code is required'}, status=400)
        if not payment_type:
            return JsonResponse({'error': 'PaymentType is required'}, status=400)
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
            branch_code=branch_code,
            consultationFee=consultationFee
        )
        billing_data.save()
        return JsonResponse({'success': 'Billing data saved successfully!', 'consumerBillNumber': consumer_bill_number, 'procedureBillNumber': procedure_bill_number}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)



from collections import defaultdict
@csrf_exempt
def medical_history(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    data = json.loads(request.body)
    patientUID = data.get('id')
    branch_code = data.get('branch_code')

    if not patientUID or not branch_code:
        return JsonResponse({'error': 'patientUID and branch_code are required'}, status=400)

    summary_qs = SummaryDetail.objects.filter(patientUID=patientUID, branch_code=branch_code).values()
    billing_qs = BillingData.objects.filter(patientUID=patientUID, branch_code=branch_code).values()
    procedure_qs = ProcedureBill.objects.filter(patientUID=patientUID, branch_code=branch_code).values()

    history_map = defaultdict(lambda: {
        "appointmentDate": "",
        "summary": None,
        "billing": None,
        "procedure": None
    })

    for item in summary_qs:
        date = item.get('appointmentDate')
        history_map[date]['appointmentDate'] = date
        history_map[date]['summary'] = item

    for item in billing_qs:
        date = item.get('appointmentDate')
        history_map[date]['appointmentDate'] = date
        history_map[date]['billing'] = item

    for item in procedure_qs:
        date = item.get('appointmentDate')
        history_map[date]['appointmentDate'] = date
        history_map[date]['procedure'] = item

    merged_result = []

    for date, data in history_map.items():
        summary = data['summary']
        billing = data['billing']
        procedure = data['procedure']

        billing_NA = billing and billing.get("patient_handledby") == "N/A"
        procedure_NA = procedure and procedure.get("patient_handledby") == "N/A"

        # CASE 1: If summary exists → show only summary (even if billing/procedure exist)
        if summary:
            merged_result.append({
                "appointmentDate": date,
                "summary": summary,
                "billing": None,
                "procedure": None,
                "type": "summary_only"
            })
        # CASE 2: No summary, but billing & procedure both exist and both are N/A
        elif billing_NA and procedure_NA:
            merged_result.append({
                "appointmentDate": date,
                "summary": None,
                "billing": billing,
                "procedure": procedure,
                "type": "billing_procedure_NA"
            })
        # CASE 3: No summary, only billing with N/A
        elif billing_NA and not procedure:
            merged_result.append({
                "appointmentDate": date,
                "summary": None,
                "billing": billing,
                "procedure": None,
                "type": "billing_only_NA"
            })
        # CASE 4: No summary, only procedure with N/A
        elif procedure_NA and not billing:
            merged_result.append({
                "appointmentDate": date,
                "summary": None,
                "billing": None,
                "procedure": procedure,
                "type": "procedure_only_NA"
            })
        # CASE 5: No valid data (or invalid handled by someone else)
        else:
            continue  # Skip cases not meeting the conditions

    result = sorted(merged_result, key=lambda x: x['appointmentDate'], reverse=True)
    return JsonResponse(result, safe=False)