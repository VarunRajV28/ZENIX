docker exec momwatch_mongodb mongosh momwatch_db --quiet --eval "db.users.updateMany({role: 'mother'}, {\$set: {role: 'asha'}})"
docker exec momwatch_mongodb mongosh momwatch_db --quiet --eval "db.users.find({}, {email:1, role:1, _id:0})"
