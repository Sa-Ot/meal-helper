import json
import os
import random

import requests
from flask import Flask, render_template, jsonify, abort, request, redirect, url_for

app = Flask(__name__)

BASE_URL = "https://www.themealdb.com/api/json/v1/1"
PERSONAL_FILE = "personal_recipes.json"


def load_personal():
    if not os.path.exists(PERSONAL_FILE):
        return []
    with open(PERSONAL_FILE) as f:
        return json.load(f)


def save_personal(recipes):
    with open(PERSONAL_FILE, "w") as f:
        json.dump(recipes, f, indent=2)


def find_personal(name):
    for r in load_personal():
        if r["name"] == name:
            return r
    return None


def get_recipe_for(main_ingredient: str) -> dict:
    response = requests.get(f"{BASE_URL}/filter.php", params={"i": main_ingredient})
    meals = response.json()["meals"] or []

    wanted = main_ingredient.replace("_", " ").lower()
    personal = [r for r in load_personal()
                if any(wanted == i.lower() for i in r["ingredients"])]

    options = [("api", m) for m in meals] + [("personal", r) for r in personal]
    if not options:
        return None

    source, chosen = random.choice(options)
    if source == "personal":
        return chosen

    response = requests.get(f"{BASE_URL}/lookup.php", params={"i": chosen["idMeal"]})
    meal = response.json()["meals"][0]

    ingredients = {}
    for i in range(1, 21):
        name = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")
        if name and name.strip():
            ingredients[name] = measure

    return dict(
        name=meal["strMeal"],
        image=meal["strMealThumb"],
        video=meal["strYoutube"],
        instructions=meal["strInstructions"],
        ingredients=ingredients,
    )


@app.route('/')
def index():
    return render_template("index.html")


@app.route("/recipe/<ingredient>")
def recipe(ingredient):
    found = get_recipe_for(ingredient)
    if found is None:
        abort(404)
    return render_template("recipe.html", ingredient=ingredient, recipe=found)


@app.route("/recipe/<ingredient>/json")
def recipe_json(ingredient):
    found = get_recipe_for(ingredient)
    if found is None:
        abort(404)
    return jsonify(found)


@app.route("/personal", methods=["POST"])
def add_personal():
    new_recipe = request.get_json()
    recipes = load_personal()
    recipes.append(new_recipe)
    save_personal(recipes)
    return redirect(url_for("get_personal", name=new_recipe["name"], json=0))


@app.route("/personal/<name>/<int:json>")
def get_personal(name, json):
    found = find_personal(name)
    if found is None or json not in (0, 1):
        abort(404)
    if json == 1:
        return jsonify(found)
    return render_template("recipe.html", ingredient=name, recipe=found)


@app.route("/personal/<name>", methods=["DELETE"])
def delete_personal(name):
    recipes = load_personal()
    remaining = [r for r in recipes if r["name"] != name]
    if len(remaining) == len(recipes):
        abort(404)
    save_personal(remaining)
    return jsonify(deleted=name)


@app.route("/personal/all")
def all_personal():
    return jsonify(load_personal())


if __name__ == '__main__':
    app.run(debug=True, port=5001)