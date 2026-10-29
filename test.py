from agents.challenge_generator import challenge_generator
from agents.code_evaluator import code_evaluator
from agents.theory_expert import answer_textbook_query


res = answer_textbook_query("What is Binary Search Tree")

print(res)










# res = challenge_generator("""You are a Curriculum Designer. Based on the topic 'Binary Trees', 
#     generate a LeetCode-style challenge. Provide a description, function signature, and 3 test cases.""")


# question = "Find the node in a Binary Search Tree (BST) where the node's value equals val, and return that subtree; return None if the node doesn't exist. BST properties ensure left child nodes are smaller and right child nodes are larger than the parent." 

# answer = """ class Solution:
#     def searchBST(self, root: Optional[TreeNode], val: int) -> Optional[TreeNode]:
#         current = root
#         while current is not None:
#             if current.val == val:
#                 return current
#             elif val < current.val:
#                 current = current.left
#             else:
#                 current = current.right
#         return None 
#         """


# res = code_evaluator(f"Evaluate this code: {answer} against this challenge: {question}")

# print(res)
