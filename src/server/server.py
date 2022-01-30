import multiprocessing
from flask import Flask, jsonify, request
from core.blockchain import Blockchain
from uuid import uuid4
from urllib.parse import urlparse
import sys
import time

import requests

blockchain = Blockchain()

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
node_address = str(uuid4()).replace('-', '')

def bootstrap_core_network():
    #TODO: Make host configurable to remove centralized authority
    port = int(sys.argv[1])
    requests.post(f'http://127.0.0.1:5000/connect_node',
                  json={'nodes': [f'http://127.0.0.1:{port}']})

@app.route('/mine_block', methods=['GET'])
def mine_block():
    print(urlparse(request.url))
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)

    response = {
        'message': 'Congratulations, you have mined a block successfully',
        'index': block['index'],
        'timestamp': block['timestamp'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
        'transactions': block['transactions']
    }

    chain_synced = blockchain.chain_sync()

    if (chain_synced == False):
        return jsonify(response), 400

    return jsonify(response), 201


@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }

    return jsonify(response), 200


@app.route('/check_chain', methods=['GET'])
def check_blockchain_validity():
    valid = blockchain.is_chain_valid(blockchain.chain)
    if valid:
        return {'message': 'Blockchain is valid'}, 200

    return {'message': 'Blockchain is NOT VALID'}, 400


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']

    if not all(key in json for key in transaction_keys):
        return 'Transaction schema malformed', 400

    index = blockchain.add_transaction(
        json['sender'],
        json['receiver'],
        json['amount']
    )

    response = {
        'message': f'Transaction added to index: {index}'
    }

    return response, 201


@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    print(f'received {nodes}')

    if nodes is None:
        return 'No node IP or DNS supplied', 400

    for node in nodes:
        stripped_node = urlparse(node)
        try:
            print(stripped_node.netloc)
            print(blockchain.nodes)
            if stripped_node.netloc not in blockchain.nodes:
                response = requests.get(f'{node}/health')
                if (response.status_code == 200):
                    blockchain.add_node(node)
                    requests.post(f'{node}/connect_node',
                                  json={'nodes': ["http://127.0.0.1:" + sys.argv[1]]})
                else:
                    # TODO: Need a remove_node function to remove off blockchain
                    print('na')
        except Exception as e:
            print(e)

    for node in blockchain.nodes:
        if node not in nodes:
            for input_node in nodes:
                requests.post(f'http://{node}/connect_node',
                                json={'nodes': [input_node]})

    response = {
        'message': 'Nodes in network successfully connected',
        'total_nodes': list(blockchain.nodes),
        'network_size': len(blockchain.nodes),
    }

    return jsonify(response), 201


@app.route('/get_nodes', methods=['GET'])
def get_nodes():

    response = {
        'total_nodes': list(blockchain.nodes),
        'network_size': len(blockchain.nodes),
        'server_address': node_address
    }

    return jsonify(response), 200


@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    response = None

    if is_chain_replaced:
        response = {
            'message': 'The node has different chains, we have replaced with the longest chain',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Chain did not need to be updated, this is the longest chain',
            'actual_chain': blockchain.chain
        }

    return response, 200


@app.route('/health', methods=['GET'])
def health():
    response = {
        'message': 'online'
    }

    return response, 200


def init():
    app.run(host='0.0.0.0', port=sys.argv[1])

if __name__ == "__main__":
    p = multiprocessing.Process(target=init, args=())
    p.start()
    time.sleep(2)
    bootstrap_core_network()
