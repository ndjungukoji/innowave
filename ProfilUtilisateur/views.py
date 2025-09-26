from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from .models import Utilisateur, HistoriqueConnexion
from django.core.mail import send_mail
from django.conf import settings
import json
import base64
from django.core.files.base import ContentFile
 # Assure-toi que Profile est bien importé

def login_view(request):
    """
    Affiche le formulaire de connexion. Si les identifiants sont corrects, redirige vers la page d'accueil.
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    return render(request, "ProfilUtilisateur/login.html")

def register(request):
    if request.method == 'POST':
        # Récupération des champs du formulaire
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        bio = request.POST.get('bio', '')
        date_naissance = request.POST.get('date_naissance', None)
        adresse = request.POST.get('adresse', '')
        telephone = request.POST.get('telephone', '')
        genre = request.POST.get('genre', '')
        image = request.FILES.get('image')
        cover_image = request.FILES.get('cover_image')

        # Gestion des réseaux sociaux (nouveau format)
        facebook = request.POST.get('facebook', '').strip()
        instagram = request.POST.get('instagram', '').strip()
        twitter = request.POST.get('twitter', '').strip()
        reseaux_sociaux_dict = {}
        if facebook:
            reseaux_sociaux_dict['facebook'] = facebook
        if instagram:
            reseaux_sociaux_dict['instagram'] = instagram
        if twitter:
            reseaux_sociaux_dict['twitter'] = twitter

        # Validation des mots de passe
        if password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return render(request, 'ProfilUtilisateur/register.html')

        # Vérification que le nom d'utilisateur et l'email ne sont pas déjà utilisés
        if Utilisateur.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
            return render(request, 'ProfilUtilisateur/register.html')

        if Utilisateur.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return render(request, 'ProfilUtilisateur/register.html')

        try:
            # Création de l'utilisateur
            user = Utilisateur.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                bio=bio,
                date_naissance=date_naissance,
                adresse=adresse,
                telephone=telephone,
                genre=genre,
                image=image,
                cover_image=cover_image,
                reseaux_sociaux=reseaux_sociaux_dict  # Enregistrement sous forme de JSON
            )

            # Envoi d'un email à l'entreprise pour signaler l'inscription
            try:
                send_mail(
                    subject='Nouvelle inscription sur le site',
                    message=f"Un nouvel utilisateur vient de s'inscrire : {username} ({email})",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_NOTIFICATION_EMAIL],
                    fail_silently=True,
                )
            except Exception as e:
                # Optionnel : log ou message d'erreur pour l'admin
                pass

            # Redirige vers la page de connexion avec un paramètre GET pour afficher le message de succès
            return redirect('/login/?inscription=ok')
        
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite : {e}")

    return render(request, 'ProfilUtilisateur/register.html')


def home(request):
    """
    Page d'accueil accessible sans authentification.
    """
    return render(request, "ProfilUtilisateur/home.html")

def apropos(request):
    return render(request, 'ProfilUtilisateur/apropos.html')

def contact(request):
    return render(request, 'ProfilUtilisateur/contact.html')

@login_required
def profile(request, slug):
    profile = get_object_or_404(Utilisateur, slug=slug)
    return render(request, 'ProfilUtilisateur/profile.html', {'profile': profile})

@login_required
def user_list(request):
    search_query = request.GET.get('search', '')
    users = Utilisateur.objects.all()

    if search_query:
        users = users.filter(username__icontains=search_query)  # Correction ici !

    return render(request, 'ProfilUtilisateur/user_list.html', {'users': users, 'search_query': search_query})



@login_required
def change_profile_image(request):
    # NOTE: This endpoint acts on the currently authenticated user (request.user)
    # and does not accept a user identifier. This prevents modifying other users' images.
    # Keep @login_required to ensure only authenticated users can call it.
    if request.method == "POST":
        # Utilisateur connecté
        user = request.user

        # Legacy: upload direct file (cover image)
        if 'cover_image' in request.FILES:
            user.cover_image = request.FILES['cover_image']
            user.save()
            return redirect('profile', slug=user.slug)

        # Handle cropped image sent as DataURL (base64)
        cropped = request.POST.get('cropped_image')
        image_type = request.POST.get('image_type', 'profile')  # 'profile' or 'cover'
        if cropped:
            try:
                # Expecting data like: data:image/png;base64,....
                header, imgstr = cropped.split(';base64,')
                ext = header.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f"{user.username}_{image_type}.{ext}")
                if image_type == 'cover':
                    user.cover_image.save(data.name, data, save=True)
                else:
                    user.image.save(data.name, data, save=True)
                messages.success(request, "Image mise à jour avec succès.")
            except Exception as e:
                messages.error(request, f"Impossible de traiter l'image : {e}")

        return redirect('profile', slug=user.slug)
    return redirect('profile', slug=request.user.slug)

@login_required
def delete_profile_image(request):
    # NOTE: Deletes image for request.user only. This route is intentionally
    # bound to the authenticated user and will not delete images of other users.
    if request.method == 'POST':
        request.user.image = None  # Supprime l'image
        request.user.save()
        messages.success(request, "Photo de profil supprimée avec succès.")
    return redirect('profile', slug=request.user.slug)

@login_required
def edit_profile(request):
    # NOTE: Editing applies to the current logged-in user (request.user) only.
    # If you later add admin-editing of other profiles, implement explicit
    # permission checks and accept a 'slug' parameter.
    user = request.user
    if request.method == 'POST' and request.FILES.get('image'):
        user.image = request.FILES['image']
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.bio = request.POST.get('bio', user.bio)
        user.telephone = request.POST.get('telephone', user.telephone)
        user.adresse = request.POST.get('adresse', user.adresse)
        user.date_naissance = request.POST.get('date_naissance', user.date_naissance)
        user.genre = request.POST.get('genre', user.genre)
        user.save()
        messages.success(request, "Profil mis à jour avec succès.")
        return redirect('profile', slug=user.slug)
    return render(request, 'ProfilUtilisateur/edit_profile.html', {'user': user})

@login_required
def delete_account(request):
    # NOTE: Deletes the currently authenticated user's account only.
    if request.method == 'POST':
        user = request.user
        user.delete()
        messages.success(request, "Votre compte a été supprimé avec succès.")
        return redirect('login')
    return redirect('profile', slug=request.user.slug)

@login_required
def profile_details(request, slug):
    try:
        utilisateur = Utilisateur.objects.get(slug=slug)
    except Utilisateur.DoesNotExist:
        return HttpResponse(f"Utilisateur avec le slug '{slug}' non trouvé.", status=404)

    # Renvoyer les informations au template
    return render(request, 'ProfilUtilisateur/profile_details.html', {'utilisateur': utilisateur})

@login_required
def historique_connexion(request):
    historiques = HistoriqueConnexion.objects.filter(utilisateur=request.user)
    return render(request, 'ProfilUtilisateur/historique_connexion.html', {'historiques': historiques})

def logout_view(request):
    logout(request)
    return redirect('login')

def services(request):
    """
    Affiche la page des services.
    """
    return render(request, "ProfilUtilisateur/services.html")


def terms(request):
    """Affiche les termes et conditions (CGU)."""
    return render(request, 'ProfilUtilisateur/terms.html')