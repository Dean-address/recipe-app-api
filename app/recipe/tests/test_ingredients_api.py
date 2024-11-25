"""
Test for the ingredient API
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe,
)
from recipe.serializers import IngredientSerializer

INGREDIENT_URL = reverse("recipe:ingredient-list")


def detail_url(ingredient_id):
    """Create and return an ingredient detail URL."""
    return reverse("recipe:ingredient-detail", args=[ingredient_id])


def create_user(email="user@example.com", password="testpass123"):
    """Create and return a new user"""
    return get_user_model().objects.create(email=email, password=password)


class PublicIngredientApiTests(TestCase):
    """Test unautenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrivrving ingredients"""
        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test authenticated API reqests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving a list of ingredients"""
        Ingredient.objects.create(user=self.user, name="Kale")
        Ingredient.objects.create(user=self.user, name="Vanilla")

        res = self.client.get(INGREDIENT_URL)

        ingredient = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredient, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test list of ingredient is limited to authenticated user"""
        user2 = create_user(email="user2@example.com")
        Ingredient.objects.create(user=user2, name="Salt")
        ingredient = Ingredient.objects.create(user=self.user, name="Pepper")

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], ingredient.name)
        self.assertEqual(res.data[0]["id"], ingredient.id)

    def test_update_ingredient(self):
        """Test updaing an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name="Cilantro")

        payload = {
            "name": "Coriander",
        }
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload["name"])

    def test_delete_ingredient(self):
        """Test deleting an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name="Lettuce")

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingredients by those assigned to recipes"""
        in1 = Ingredient.objects.create(user=self.user, name="Apples")
        in2 = Ingredient.objects.create(user=self.user, name="Turkey")

        recipe = Recipe.objects.create(
            title="Apple Crumble",
            time_minutes=5,
            price=Decimal("4.50"),
            user=self.user,
        )
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENT_URL, {"assigned_only": 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients return a unique list"""
        ing = Ingredient.objects.create(user=self.user, name="Eggs")
        Ingredient.objects.create(user=self.user, name="Lentils")

        r1 = Recipe.objects.create(
            title="Eggs Benedict",
            time_minutes=60,
            price=Decimal("7.00"),
            user=self.user,
        )
        r2 = Recipe.objects.create(
            title="Herbs Egg",
            time_minutes=20,
            price=Decimal("4.00"),
            user=self.user,
        )
        r1.ingredients.add(ing)
        r2.ingredients.add(ing)

        res = self.client.get(INGREDIENT_URL, {"assigned_only": 1})

        self.assertEqual(len(res.data), 1)
