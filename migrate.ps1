$updateCommand = 'db.users.updateMany({role: \"mother\"}, {\"$set\": {role: \"asha\"}})'
$findCommand = 'db.users.find({}, {email:1, role:1, _id:0})'

Write-Host "Updating mother roles to asha..."
docker exec momwatch_mongodb mongosh momwatch_db --quiet --eval $updateCommand

Write-Host "`nListing all users:"
docker exec momwatch_mongodb mongosh momwatch_db --quiet --eval $findCommand
