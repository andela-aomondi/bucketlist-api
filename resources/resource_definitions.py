"""Import statements."""
from models.bucketlist_model import User, BucketList, BucketListItem, app, db
from flask_restful import Resource, Api, marshal_with, marshal
from flask import request, jsonify, session
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
from flask.ext.httpauth import HTTPBasicAuth
from helpers.random_string_generator import id_generator
from helpers.marshal_fields import bucketlistitem_serializer,\
    bucketlist_serializer

# create auth object
auth = HTTPBasicAuth()

# create the api object
api = Api(app)


# API ROUTES #
@auth.verify_password
def verify_password(token, password):
    """
    Take the token or password and verify that it is valid.

    Args:
        token: The token generated
        password: (optional) The users password

    Returns:
        True if user exists and token is valid
        False if user is nonexistent or token is invalid
    """
    # authenticate by token
    token = request.headers.get('Authorization')

    if not token:
        return False

    user = User.verify_auth_token(token)

    if user:
        return True
    else:
        return False


class Home(Resource):
    """
    Handles requests to home route.

    Resource url:
        '/'

    Endpoint:
        'home'

    Requests Allowed:
        GET
    """

    def get(self):
        """
        Handle get requests to home route '/'

        Args:
            self

        Returns:
            A json encoded welcome message
        """
        return jsonify({"message": "Welcome to the bucketlist API."
                        "" + " Send a POST request to /auth/login "
                        "" + "with your login details "
                        "" + "to get started."})


class Login(Resource):
    """
    Handles login requests.

    Resource url:
        '/auth/login'

    Endpoint:
        'login'

    Requests Allowed:
        'POST'
    """

    def post(self):
        """
        Login a user and return a token.

        Args:
            self

        Returns:
            A token to be used for every request

        Raises:
            401 error when invalid credentials given
        """
        # get user login data from request
        json_data = request.get_json()

        if "username" in json_data and "password" in json_data:
            # set uname and pword
            uname = json_data['username']
            pword = json_data['password']
        else:
            return {"message": "Provide both a username and a password."}, 401

        # select user from db based on username
        user = User.query.filter_by(username=uname).first()

        # check if the user's password matches the one entered
        result = user.verify_password(pword)

        # if result will be true, generate a token
        if result:
            session['user_id'] = user.id
            session['serializer_key'] = id_generator()

            s = Serializer(session['serializer_key'], expires_in=6000)
            token = s.dumps({'id': user.id})
            return jsonify({"token": token})

        return jsonify({"message": "Invalid login details."})


class Logout(Resource):
    """
    Handles logout requests.

    Resource url:
        '/auth/logout'

    Endpoint:
        'logout'

    Requests Allowed:
        'GET'
    """

    @auth.login_required
    def get(self):
        """
        Logout a user and return a message.

        Args:
            self

        Returns:
            A success message on logout.
        """
        # replace the serializer_key with an invalid one
        session['serializer_key'] = id_generator()
        del session['user_id']

        return jsonify({"message": "You have been logged out successfully."})


class Allbucketlists(Resource):
    """
    Handles actions on bucketlists.

    Resource url:
        '/bucketlists/'

    Endpoint:
        'bucketlists'

    Requests Allowed:
        'GET', 'POST'
    """

    @auth.login_required
    def get(self):
        """
        Query all bucketlists.

        Args:
            self

        Return:
            All bucketlists belonging to the logged in user.
        """
        # get id of logged in user
        uid = session['user_id']
        # if limit exists, assign it to limit
        try:
            limit = int(request.args.get('limit', 20))

            if limit < 1:
                limit = 20

            if limit > 100:
                limit = 100
        except:
            limit = 20
        # if q exists, assign it to q
        q = request.args.get('q')
        # if page exists, assign it to page
        try:
            page = int(request.args.get('page'))
        except:
            page = 1

        # when q is defined, search for relevant bucketlists
        if q is not None:
            bucketlists = BucketList.query.filter_by(created_by=uid).all()

            # will hold all bucketlists that meet search criteria
            listOfResults = []

            for bucket in bucketlists:
                if q in bucket.name:
                    listOfResults.append(bucket)

            return marshal(listOfResults, bucketlist_serializer)

        # if limit and search query are not specified,
        # query and return all bucketlists
        bucketlists = BucketList.query.filter_by(created_by=uid).paginate(page, limit, False).items

        return marshal(bucketlists, bucketlist_serializer)

    @auth.login_required
    def post(self):
        """
        Create a new bucketlist.

        Args:
            self

        Returns:
            A message on success.
        """
        # get data from json request
        json_data = request.get_json()
        # get name of bucketlist from json data
        name = json_data['name']
        # get owner id from logged in user session
        uid = session['user_id']

        # create the bucketlist using the relevant data
        blist = BucketList(name, uid)

        # commit bucketlist to db
        db.session.add(blist)
        db.session.commit()

        return jsonify({'message': 'Bucketlist created successfully.'})


class Onebucketlist(Resource):
    """
    Handle actions on individual bucketlists.

    Resource url:
        '/bucketlists/<id>'

    Endpoint:
        'bucketlist'

    Requests Allowed:
        'GET', 'DELET','PUT'
    """

    @auth.login_required
    def get(self, id):
        """
        Query one bucketlist by ID.

        Args:
            self
            id: The bucketlist id

        Returns:
            The required bucketlist details.

        Raises:
            404 nothing found error.
        """
        # get id of logged in user
        uid = session['user_id']

        bucketlist = BucketList.query.filter_by(created_by=uid, bid=id).first()

        if bucketlist is not None:
            return marshal(bucketlist, bucketlist_serializer)

        return {"Error": "Nothing found"}, 404

    @auth.login_required
    def put(self, id):
        """
        Update one bucketlist using its ID.

        Args:
            self
            id: ID of the bucketlist to be updated.

        Returns:
            The updated bucketlist details.

        Raises:
            404 bucketlist not found error.
        """
        # get id of logged in user
        uid = session['user_id']
        json_data = request.get_json()

        bucketlist = BucketList.query.filter_by(created_by=uid, bid=id).first()

        if bucketlist is not None:
            bucketlist.name = json_data['name']

            db.session.add(bucketlist)
            db.session.commit()

            return marshal(bucketlist, bucketlist_serializer)

        return {"Error": "Bucketlist not found"}, 404

    @auth.login_required
    def delete(self, id):
        """
        Delete a bucketlist using its ID.

        Args:
            self
            id: ID of bucketlist to be deleted.

        Returns:
            A message on successful delete operation.

        Raises:
            404 bucketlist not found error.
        """
        # get id of logged in user
        uid = session['user_id']

        bucketlist = BucketList.query.filter_by(created_by=uid, bid=id).first()

        if bucketlist is not None:
            db.session.delete(bucketlist)
            db.session.commit()

            return jsonify({'message': 'Bucketlist ' + id +
                            ' deleted successfully.'})

        return {"Error": "Bucketlist not found"}, 404


class Bucketlistitem(Resource):
    """
    Handle creation of new bucketlist items.

    Resource url:
        '/bucketlists/<id>/items/'

    Endpoint:
        'items'

    Requests Allowed:
        'POST'
    """

    @auth.login_required
    def post(self, id):
        """
        Create a new bucketlist item.

        Args:
            self
            id: ID of the bucketlist item is to be created in.

        Returns:
            The updated bucketlist showing the new item added.

        Raises:
            401 error if user doesn't own a bucketlist with the given ID.
        """
        # get id of logged in user
        uid = session['user_id']
        # get the data for new item from request
        json_data = request.get_json()
        # item data
        itemname = json_data['name']

        # confirm user actually owns the bucketlist to be modified
        bucketlist = BucketList.query.filter_by(created_by=uid, bid=id).first()

        if bucketlist is not None:
            # create the new bucketlist item
            newitem = BucketListItem(itemname, id)
        else:
            return {"message": "You do not own a"
                    " " + "bucketlist with id " + str(id)}, 401

        # save the item in the database
        db.session.add(newitem)
        db.session.commit()

        # get the updated bucketlist and return it
        updatedBucketList = \
            BucketList.query.filter_by(created_by=uid, bid=id).first()

        return marshal(updatedBucketList, bucketlist_serializer)


class Bucketitemsactions(Resource):
    """
    Handle actions on bucketlist items.

    Resource url:
        '/bucketlists/<id>/items/<item_id>'

    Endpoint:
        'item'

    Requests allowed:
        'PUT', 'DEL'
    """

    @auth.login_required
    def put(self, id, item_id):
        """
        Update a bucketlist item.

        Args:
            self
            id: The id of the bucketlist item belongs to.
            item_id: The ID of the item to be deleted.

        Returns:
            The updated item.

        Raises:
            404 error if the bucketlist is not found.
        """
        # get id of logged in user
        uid = session['user_id']
        # select the item from database for modification
        bucketlist = BucketList.query.filter_by(created_by=uid, bid=id).first()

        # if logged in user owns the bucketlist
        if bucketlist:
            item = BucketListItem.query.filter_by(bid=id, iid=item_id).first()
            # get update data from request
            json_data = request.get_json()

            # update item
            if item is not None:
                if 'name' in json_data:
                    item.name = json_data['name']

                if 'done' in json_data:
                    if json_data['done'] == "True" or json_data['done'] == "False":
                        item.done = json_data['done']
                    else:
                        item.done = "False"

                db.session.add(item)
                db.session.commit()

                return marshal(item, bucketlistitem_serializer)

        return {"Error": "Bucketlist item not found"}, 404

    @auth.login_required
    def delete(self, id, item_id):
        """
        Delete a bucketlist item using its ID.

        Args:
            self
            id: The id of the bucketlist item belongs to.
            item_id: The ID of the item to be deleted.

        Returns:
            Message on success.

        Raises:
            404 error if bucketlist or the item are not found.
        """
        # get id of logged in user
        uid = session['user_id']
        # select the item from database for modification
        bucketlist = BucketList.query.filter_by(created_by=uid, bid=id).first()

        if bucketlist:
            item = BucketListItem.query.filter_by(bid=id, iid=item_id).first()

            if item:
                db.session.delete(item)
                db.session.commit()

                return jsonify({'message': 'Item ' + item_id +
                                ' from bucketlist ' + id +
                                ' deleted successfully.'})
            else:
                return {"Error": "Bucketlist has"
                        " " + "no item with id " + str(item_id)}, 404

        return {"Error": "Bucketlist not found"}, 404

# ADD RESOURCES TO API OBJECT
api.add_resource(Home, '/', endpoint='home')
api.add_resource(Allbucketlists, '/bucketlists/', endpoint='bucketlists')
api.add_resource(Onebucketlist, '/bucketlists/<id>', endpoint='bucketlist')
api.add_resource(Bucketlistitem, '/bucketlists/<id>/items/', endpoint='items')
api.add_resource(Bucketitemsactions, '/bucketlists/<id>/items/<item_id>',
                 endpoint='item')
api.add_resource(Login, '/auth/login', endpoint='login')
api.add_resource(Logout, '/auth/logout', endpoint='logout')
