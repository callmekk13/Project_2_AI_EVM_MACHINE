from django.shortcuts import HttpResponse, render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings 
from django.core.mail import EmailMessage 
from django.db.models import Count
from django.views.decorators.http import require_POST
from threading import Thread
from .models import Voter, Party, Vote

try:
    from mailjet_rest import Client
except ImportError:
    Client = None


'''
1. Persons detections
2. Mask detection
3. Face Recognition
4. Vote 
'''

PHASES = [
    {
        'key': 'phase_1',
        'title': 'Person Detection',
        'description': 'Confirm exactly one voter is present in the booth.',
        'stream': 'detect_person',
    },
    {
        'key': 'phase_2',
        'title': 'Mask Detection',
        'description': 'Ask the voter to remove their mask for identity checks.',
        'stream': 'detect_mask',
    },
    {
        'key': 'phase_3',
        'title': 'Face Recognition',
        'description': 'Match the voter against registered constituency records.',
        'stream': 'recognize_face',
    },
    {
        'key': 'phase_4',
        'title': 'Secure Vote',
        'description': 'Record one confidential vote for an eligible voter.',
        'stream': None,
    },
]


def init_session(request):
    request.session['phase_1'] = False
    request.session['phase_2'] = False
    request.session['phase_3'] = False
    request.session['phase_4'] = False


def ensure_session(request):
    if 'phase_1' not in request.session:
        init_session(request)


def registered_names():
    return set(Voter.objects.values_list('first_name', flat=True))


def get_current_phase(request):
    ensure_session(request)
    for index, phase in enumerate(PHASES, start=1):
        phase['complete'] = bool(request.session.get(phase['key']))
        phase['active'] = not phase['complete']
        phase['number'] = index
        if phase['active']:
            return phase
    return PHASES[-1]


def build_context(request, **extra):
    current_phase = get_current_phase(request)
    
    # Determine if we should activate simulator controls
    import detect_person.camera as dp_cam
    import detect_mask.camera as dm_cam
    import recognize_face.camera as rf_cam
    camera_failed = dp_cam.CAMERA_FAILED or dm_cam.CAMERA_FAILED or rf_cam.CAMERA_FAILED
    
    # Ensure default simulation variables exist in session
    if 'sim_persons' not in request.session:
        request.session['sim_persons'] = 1
    if 'sim_has_mask' not in request.session:
        request.session['sim_has_mask'] = False
    if 'sim_face_name' not in request.session:
        request.session['sim_face_name'] = 'Ankit'
        
    context = {
        'stream': current_phase['stream'],
        'phase': current_phase,
        'phases': PHASES,
        'total_voters': Voter.objects.count(),
        'total_parties': Party.objects.count(),
        'total_votes': Vote.objects.count(),
        'camera_failed': camera_failed or True, # Force show simulator widget to allow full client-side control
        'voter_names': sorted(list(registered_names())),
        'sim_persons': request.session.get('sim_persons', 1),
        'sim_has_mask': request.session.get('sim_has_mask', False),
        'sim_face_name': request.session.get('sim_face_name', 'Ankit'),
    }
    context.update(extra)
    return context


def render_index(request, **extra):
    return render(request, 'index.html', build_context(request, **extra))


def start(request):
    ensure_session(request)

    if request.method == 'POST':
        if not request.session['phase_1']:
            # get # of persons
            import detect_person.camera as dp_cam
            persons = request.session.get('sim_persons', dp_cam.PERSON_COUNT)
            if dp_cam.CAMERA_FAILED and 'sim_persons' not in request.session:
                persons = 1
            request.session['persons'] = persons
            print('PERSONS:', persons)

            if persons == 1:
                messages.success(request, 'Persons Detection Phase completed')
                request.session['phase_1'] = True
                return render_index(request)
            else:
                messages.error(request, 'Exactly one person must be in the Polling Booth!')
                return render_index(request)

        elif not request.session['phase_2']:
            # get mask status
            import detect_mask.camera as dm_cam
            has_mask = request.session.get('sim_has_mask', dm_cam.HAS_MASK)
            if dm_cam.CAMERA_FAILED and 'sim_has_mask' not in request.session:
                has_mask = False
            request.session['has_mask'] = has_mask
            print('HAS_MASK:', has_mask)

            if not has_mask:
                # mark as complete & render phase-3
                messages.success(request, 'Mask Detection Phase completed')
                request.session['phase_2'] = True
                return render_index(request)
            else:
                # revert back to same phase
                messages.warning(request, 'Please remove your mask for identity verification!')
                return render_index(request)
        
        elif not request.session['phase_3']:
            # get face name
            import recognize_face.camera as rf_cam
            face_name = request.session.get('sim_face_name', rf_cam.FACE_NAME)
            if rf_cam.CAMERA_FAILED and 'sim_face_name' not in request.session:
                face_name = 'Ankit'
            request.session['face_name'] = face_name
            print('FACE_NAME:', face_name)

            if face_name in registered_names():
                # mark as complete & move to phase_4 (voting)
                messages.success(request, 'Face Recognition Phase completed')
                request.session['phase_3'] = True
                # if already voted clear session & send back to main page
                request.method = 'GET'
                return start(request)
            else:
                messages.error(request, 'Your nomination is not in this constituency!')
                return render_index(request)

        elif not request.session['phase_4']:
            if 'voted_to' not in request.POST:
                messages.warning(request, 'Please select a candidate before submitting your vote.')
                return render_index(request, pts=Party.objects.all())

            voted_to = Party.objects.get(name=request.POST['voted_to'])
            voter = Voter.objects.get(first_name=request.session['face_name'])
            Vote(voter=voter, voted_to=voted_to).save()
            Thread(target= success, args=(voter, voted_to.full_name)).start()
            messages.success(request, 'Thank you! Your vote has been recorded successfully!')
            request.session.flush()
            request.method = 'GET'
            return start(request)
        
        else:
            return HttpResponse('No suitable POST condition satisfied!')

    else:
        if not request.session['phase_1']:
            return render_index(request)
        if not request.session['phase_2']:
            return render_index(request)
        if not request.session['phase_3']:
            return render_index(request)
        if not request.session['phase_4']:
            if len(Vote.objects.filter(voter__first_name=request.session['face_name'])) > 0:
                messages.error(request, 'Sorry, you have already voted!')
                request.session.flush()
                request.method = 'GET'
                return start(request)
            else:
                return render_index(request, pts=Party.objects.all())




def dbg(request):
    return JsonResponse(dict(request.session))


def api_status(request):
    current_phase = get_current_phase(request)
    return JsonResponse({
        'current_phase': current_phase['key'],
        'current_title': current_phase['title'],
        'phases': [
            {
                'key': phase['key'],
                'title': phase['title'],
                'complete': bool(request.session.get(phase['key'])),
                'active': phase['key'] == current_phase['key'],
            }
            for phase in PHASES
        ],
        'session': {
            'persons': request.session.get('persons'),
            'has_mask': request.session.get('has_mask'),
            'face_name': request.session.get('face_name'),
        },
        'stats': {
            'voters': Voter.objects.count(),
            'parties': Party.objects.count(),
            'votes': Vote.objects.count(),
        }
    })


def api_results(request):
    results = (
        Party.objects
        .annotate(vote_count=Count('to'))
        .values('name', 'full_name', 'vote_count')
        .order_by('-vote_count', 'name')
    )
    return JsonResponse({'results': list(results)})


@require_POST
def reset_session(request):
    request.session.flush()
    request.session['sim_persons'] = 1
    request.session['sim_has_mask'] = False
    request.session['sim_face_name'] = 'Ankit'
    messages.info(request, 'Session reset. Start the verification flow again.')
    return redirect('start')


@require_POST
def set_sim_state(request):
    if 'sim_persons' in request.POST:
        request.session['sim_persons'] = int(request.POST['sim_persons'])
    if 'sim_has_mask' in request.POST:
        request.session['sim_has_mask'] = request.POST['sim_has_mask'] == 'true'
    if 'sim_face_name' in request.POST:
        request.session['sim_face_name'] = request.POST['sim_face_name']
    return redirect('start')


@require_POST
def clear_votes(request):
    Vote.objects.all().delete()
    messages.success(request, 'All vote records in the database have been cleared! You can now test voting again.')
    return redirect('start')


def register_voter(request):
    import os
    import base64
    import pickle
    from django.core.files.base import ContentFile
    
    if request.method == 'POST':
        epic = request.POST.get('epic')
        aadhar = request.POST.get('aadhar')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        dob = request.POST.get('dob')
        email = request.POST.get('email')

        if Voter.objects.filter(epic=epic).exists():
            messages.error(request, "EPIC Number already registered!")
            return render(request, 'register.html')

        photo_data = request.POST.get('captured_image_base64')
        image_file = None

        if photo_data and 'base64,' in photo_data:
            try:
                format, imgstr = photo_data.split(';base64,')
                ext = format.split('/')[-1]
                image_file = ContentFile(base64.b64decode(imgstr), name=f"{first_name.lower()}.{ext}")
            except Exception as e:
                messages.error(request, f"Error decoding captured photo: {str(e)}")
                return render(request, 'register.html')
        elif 'photo' in request.FILES:
            image_file = request.FILES['photo']
        else:
            messages.error(request, "Please capture a face photo or upload an image file!")
            return render(request, 'register.html')

        # Save photo file to disk
        voters_dir = os.path.join(settings.BASE_DIR, 'static', 'img', 'voters')
        if not os.path.exists(voters_dir):
            os.makedirs(voters_dir)

        image_path = os.path.join(voters_dir, f"{first_name.lower()}.jpg")
        try:
            with open(image_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)
        except Exception as e:
            messages.error(request, f"Failed to save image file: {str(e)}")
            return render(request, 'register.html')

        # Biometric Face Encoding
        biometrics_success = False
        try:
            import face_recognition
            if face_recognition is not None:
                img = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(img)
                if len(encodings) > 0:
                    new_encoding = encodings[0]
                    
                    # Update pickled models
                    models_dir = os.path.join(settings.BASE_DIR, 'models', 'recognize_face_models')
                    dataset_path = os.path.join(models_dir, 'dataset_faces.dat')
                    names_path = os.path.join(models_dir, 'name_faces.dat')
                    
                    faces_encodings = []
                    faces_names = []
                    
                    if os.path.exists(dataset_path):
                        with open(dataset_path, 'rb') as f_dat:
                            faces_encodings = pickle.load(f_dat)
                    if os.path.exists(names_path):
                        with open(names_path, 'rb') as f_names:
                            faces_names = pickle.load(f_names)
                            
                    faces_encodings.append(new_encoding)
                    faces_names.append(first_name)
                    
                    with open(dataset_path, 'wb') as f_dat:
                        pickle.dump(faces_encodings, f_dat)
                    with open(names_path, 'wb') as f_names:
                        pickle.dump(faces_names, f_names)
                    biometrics_success = True
                else:
                    print("Face not detected in image. Biometrics encoding skipped.")
            else:
                print("Face recognition package not available. Skipping biometrics encoding.")
        except Exception as ex:
            print(f"Exception during face encoding: {str(ex)}")

        # Create Voter in DB
        try:
            voter = Voter(
                epic=epic,
                aadhar=aadhar,
                first_name=first_name,
                last_name=last_name,
                dob=dob,
                email=email
            )
            voter.save()
            if biometrics_success:
                messages.success(request, f"Voter {first_name} registered successfully with face biometrics!")
            else:
                messages.warning(request, f"Voter {first_name} registered in database. (Biometrics skipped - face not detected or package missing)")
            return redirect('start')
        except Exception as e:
            messages.error(request, f"Database saving failed: {str(e)}")
            return render(request, 'register.html')

    else:
        return render(request, 'register.html')


def success(voter, voted_to):
    if Client is None or not settings.MAILJET_API_KEY or not settings.MAILJET_API_SECRET:
        print(f"Skipping email send for {voter.email}: Mailjet not configured")
        return

    mailjet = Client(auth=(settings.MAILJET_API_KEY, settings.MAILJET_API_SECRET), version='v3.1')
    data = {
    'Messages': [
        {
        "From": {
            "Email": "nktchhn1997@gmail.com",
            "Name": "Ankit"
        },
        "To": [
            {
            "Email": voter.email, # In future make sure to query by pk
            "Name": voter.first_name
            }
        ],
        "Subject": "Greetings AI-EVM.",
        "TextPart": "Your vote has been counted",
        "HTMLPart": f"<h3>Dear {voter.first_name}, This mail is to remind you that your vote has been taken into consideration! <br> You have voted to {voted_to} </h3><br />Thank You!",
        "CustomID": "AppGettingStartedTest"
        }
    ]
    }
    result = mailjet.send.create(data=data)
    print(result.status_code)


def results_page(request):
    return render(request, 'results.html')
