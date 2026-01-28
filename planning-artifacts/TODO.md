# TODO list

- When discarding a material batch, what do we do with the sub materials?
  - Do we also discard them?
  - Do we set their parent batch to None?
  - Do we prevent discarding if there are sub materials?
  - When discard can we increment, decrement... ? 

- Check how we manage default batch number when creating batch. 
- Do we prevent multiple batches with same batch number for same material?
- If I open the page http://dev-app.localhost:8510/notes/9f4e950d-853a-49c5-af13-63264dfe28c9 in icognito mode, I have the user not authenticate error
  - Handle the Ctrl + Z on activity deletion in the note, as the activity was deleted from DB, it can't be restored.


Pouvoir créer un aliquot d'un autre material
Sur l'aliquot pouvoir choisir une autre unité quantité

Formulaire Aliquot rendre + clair avoir une section parent et section enfant. 

La recherche de batch ne se met pas à jour
Créer le type created

Dans la note pouvoir créer un batch actuellement il faut que le batch soit existant