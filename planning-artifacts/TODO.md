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
- DO we force the batch of a material to use same unit ? If yes, we need to add the field in the batch creation and aliquot form.
- If we open a batch detail page already opened before, the info are not refresh. So in from the batch list (in the material page), if I create an activity on the batch, then go on the batch detail page, it is not refresh so the activity is not showed. 
- When deleting a batch (if it's an aliquot) the parent batch quantity should be updated.