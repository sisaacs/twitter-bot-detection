import os
import sys

import pickle

import numpy as np
import pandas as pd
import sqlite3

# append root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# global config
root_path = os.path.join(os.path.dirname(__file__), '..')
db_name = 'tbd.db'
db_path = os.path.join(root_path, db_name)

def init_database(reset=False):
    """
    If db file is not present, create it and initialize the users table
    Args:
        reset (bool): if True, delete the db file and recreate it
    """

    # check if the db file exists
    if not os.path.exists(db_path) or reset:

        # delete the db file if it exists
        if os.path.exists(db_path):
            os.remove(db_path)

        # create the db file
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # create the users table
        # user_id: twitter user id primary key
        # cluster_id: cluster id
        # label: 0 - unassigned, 1 - not bot, 2 - bot. default is 0
        # embedding: embedding of the user
        c.execute(
            """
                CREATE TABLE users (
                    user_id text,
                    cluster_id integer,
                    label integer default 0,
                    embedding blob,
                    PRIMARY KEY (user_id, cluster_id)
                )
            """
        )

        # save the changes
        conn.commit()

        # close the connection
        conn.close()

def load_clusters(clusters_path):
    """
    Args:
        clusters_path (str): path to the clusters pkl file containing the embeddings and user ids
    Returns:
        bool: True if successful, False otherwise
    """

    try:

        # open a connection to the database
        conn = sqlite3.connect(db_path)

        # get a cursor
        c = conn.cursor()
        
        with open(clusters_path, 'rb') as f:
            clusters = pickle.load(f)

        for cluster_index, cluster in enumerate(clusters):

            print(f"inserting cluster {cluster_index} with {len(cluster[1])} users")
            
            # unpack the cluster
            cluster_embeds, cluster_userids = cluster

            # number of users in this cluster
            num_users = len(cluster_userids)

            for user in range(num_users):

                # get the user id
                user_id = cluster_userids[user][1:]

                embedding = cluster_embeds[user]

                # insert the user into the database
                c.execute(
                    """
                        INSERT INTO users (user_id, cluster_id, embedding) VALUES (?, ?, ?)
                    """,
                    (user_id, cluster_index, embedding.astype(np.float32).tobytes())
                )

        # save the changes
        conn.commit()

        # close the connection
        conn.close()

        return True

    except Exception as e:
        print(f"Failed to load clusters due to error: {e}")
        return False
    
def get_cluster_embeddings(cluster_id):
    """
    Given a cluster id, get the embeddings of the users in the cluster
    Args:
        cluster_id (int): cluster id
    Returns:
        numpy.ndarray: embeddings of the users in the cluster (m, n) where m is the number of users and n is the embedding dimension
    """

    # open a connection to the database
    conn = sqlite3.connect(db_path)

    # get a cursor
    c = conn.cursor()

    # get the embeddings of the users in the cluster
    c.execute(
        """
            SELECT embedding FROM users WHERE cluster_id = ?
        """,
        (cluster_id,)
    )

    # get the embeddings
    embeddings = c.fetchall()

    # close the connection
    conn.close()

    # convert the embeddings to a numpy array from buffer
    return np.array([np.frombuffer(embedding[0], dtype=np.float32) for embedding in embeddings])


def get_cluster_userids(cluster_id):
    """
    Given a cluster id, get the user ids of the users in the cluster
    Args:
        cluster_id (int): cluster id
    Returns:
        list: list of user ids
    """

    # open a connection to the database
    conn = sqlite3.connect(db_path)

    # get a cursor
    c = conn.cursor()

    # get the user ids of the users in the cluster
    c.execute(
        """
            SELECT user_id FROM users WHERE cluster_id = ?
        """,
        (cluster_id,)
    )

    # get the user ids
    user_ids = c.fetchall()

    # convert to a list
    user_ids = [user_id[0] for user_id in user_ids]

    # close the connection
    conn.close()

    return user_ids

def get_unlabeled_clusters():
    """
    Get the clusters that have not been labeled
    Returns:
        list: list of cluster ids
    """

    # open a connection to the database
    conn = sqlite3.connect(db_path)

    # get a cursor
    c = conn.cursor()

    # get the clusters that have not been labeled
    c.execute(
        """
            SELECT DISTINCT cluster_id FROM users WHERE label = 0
        """
    )

    # get the clusters
    clusters = c.fetchall()

    # convert the clusters to a list
    clusters = [cluster[0] for cluster in clusters]

    # close the connection
    conn.close()

    return clusters

def get_user(user_id):
    """
    Return all information about a user
    Args:
        user_id (str): twitter user id
    """

    # open a connection to the database
    conn = sqlite3.connect(db_path)

    # get a cursor
    c = conn.cursor()

    # get the user
    c.execute(
        """
            SELECT * FROM users WHERE user_id = ?
        """,
        (user_id,)
    )

    # get the user
    user = c.fetchone()

    # close the connection
    conn.close()

    return user


def label_users(annot_information):
    """
    Given the annotation information from the frontend, update the database with the labels.
    First, we assign labels to user if it has been manually annotated. For the remaining users in the cluster,
    we assign the label of the majority of the users in the cluster.
    Args:
        annot_information (pd.DataFrame): annotation information from the frontend
    """

    # open a connection to the database
    conn = sqlite3.connect(db_path)

    # get a cursor
    c = conn.cursor()

    # get the cluster ids
    cluster_ids = annot_information['cluster_id'].unique()

    # iterate over the clusters
    for cluster_id in cluster_ids:

        # get the annotation information for this cluster
        cluster_annot = annot_information[annot_information['cluster_id'] == cluster_id]

        # get the user ids in this cluster
        user_ids = cluster_annot['user_id'].unique()

        # get the max label for this cluster
        max_label = cluster_annot['label'].value_counts().idxmax()

        # update db to reflect the labels for this cluster
        c.execute(
            """
                UPDATE users SET label = ? WHERE cluster_id = ?;
            """,
            (2 if max_label == 'Yes' else 1, cluster_id)
        )

        # iterate over the annotated users in this cluster and update db for each user
        for user_id in user_ids:

            # get the label for this user
            label = cluster_annot[cluster_annot['user_id'] == user_id]['label'].values[0]

            # update the db
            c.execute(
                """
                    UPDATE users SET label = ? WHERE user_id = ?;
                """,
                (2 if label == 'Yes' else 1, user_id)
            )
        
        # commit the changes
        conn.commit()

    # close the connection
    conn.close()

