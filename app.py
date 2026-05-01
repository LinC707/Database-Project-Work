from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import pymysql

app = Flask(__name__)
app.secret_key = "trading-platform-demo-secret"

# 数据库连接
def get_db():
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# 获取所有用户（下拉框用）
def get_all_users():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT user_id FROM user")
    users = cursor.fetchall()
    cursor.close()
    db.close()
    return [u['user_id'] for u in users]

# 获取所有商品
def get_all_items():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT item_id, item_name, status FROM item ORDER BY item_id")
    items = cursor.fetchall()
    cursor.close()
    db.close()
    return items

# 获取未售商品
def get_unsold_items():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT item_id, item_name, status
        FROM item
        WHERE status = '0'
        ORDER BY item_id
    """)
    items = cursor.fetchall()
    cursor.close()
    db.close()
    return items

# ------------------- 基础页面 -------------------
@app.route('/')
def index():
    module = request.args.get('module', 'list')
    if module not in ['list', 'ops', 'query', 'stats', 'views']:
        module = 'list'
    users = get_all_users()
    items = get_unsold_items()

    query_data = {
        'query_type': request.args.get('query_type', ''),
        'selected_user': request.args.get('user_id', ''),
        'user_scope': request.args.get('user_scope', 'all'),
        'title': '',
        'items': []
    }
    stats_data = {'total': None, 'by_category': [], 'avg_price': None, 'top_user': None}
    view_data = {'sold_data': [], 'unsold_data': []}

    if module == 'query':
        db = get_db()
        cursor = db.cursor()
        query_type = query_data['query_type']
        selected_user = query_data['selected_user']
        user_scope = query_data['user_scope']

        if query_type == 'unsold':
            query_data['title'] = "未售出商品"
            cursor.execute("SELECT * FROM item WHERE status='0' OR CAST(status AS UNSIGNED)=0")
            query_data['items'] = cursor.fetchall()
        elif query_type == 'sold':
            query_data['title'] = "已售商品"
            cursor.execute('''
                SELECT o.item_id, i.item_name, u.user_name, o.order_date
                FROM orders o
                JOIN item i ON o.item_id = i.item_id
                JOIN user u ON o.buyer_id = u.user_id
                ORDER BY o.order_date DESC, o.item_id
            ''')
            query_data['items'] = cursor.fetchall()
        elif query_type == 'price_gt30':
            query_data['title'] = "价格大于30元"
            cursor.execute("SELECT * FROM item WHERE price>30")
            query_data['items'] = cursor.fetchall()
        elif query_type == 'category_daily':
            query_data['title'] = "生活用品"
            cursor.execute("SELECT * FROM item WHERE category='DailyGoods'")
            query_data['items'] = cursor.fetchall()
        elif query_type == 'user' and selected_user:
            label = '全部' if user_scope == 'all' else ('已售' if user_scope == 'sold' else '未售')
            query_data['title'] = f"用户 {selected_user} 发布的商品（{label}）"
            sql = "SELECT * FROM item WHERE seller_id=%s"
            params = [selected_user]
            if user_scope == 'sold':
                sql += " AND (status='1' OR CAST(status AS UNSIGNED)=1)"
            elif user_scope == 'unsold':
                sql += " AND (status='0' OR CAST(status AS UNSIGNED)=0)"
            sql += " ORDER BY item_id"
            cursor.execute(sql, params)
            query_data['items'] = cursor.fetchall()

        cursor.close()
        db.close()

    elif module == 'stats':
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM item")
        stats_data['total'] = cursor.fetchone()['total']
        cursor.execute("SELECT category, COUNT(*) AS count FROM item GROUP BY category ORDER BY count DESC, category")
        stats_data['by_category'] = cursor.fetchall()
        cursor.execute("SELECT AVG(price) AS avg_price FROM item")
        stats_data['avg_price'] = cursor.fetchone()['avg_price']
        cursor.execute('''
            SELECT seller_id, COUNT(*) AS count
            FROM item
            GROUP BY seller_id
            ORDER BY count DESC, seller_id
            LIMIT 1
        ''')
        stats_data['top_user'] = cursor.fetchone()
        cursor.close()
        db.close()

    elif module == 'views':
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE OR REPLACE VIEW sold_view AS
            SELECT i.item_name, o.buyer_id FROM orders o
            JOIN item i ON o.item_id=i.item_id
        ''')
        cursor.execute('''
            CREATE OR REPLACE VIEW unsold_view AS
            SELECT * FROM item WHERE status='0'
        ''')
        cursor.execute("SELECT * FROM sold_view")
        view_data['sold_data'] = cursor.fetchall()
        cursor.execute("SELECT * FROM unsold_view")
        view_data['unsold_data'] = cursor.fetchall()
        db.commit()
        cursor.close()
        db.close()

    return render_template(
        'index.html',
        users=users,
        items=items,
        active_module=module,
        query_data=query_data,
        stats_data=stats_data,
        view_data=view_data
    )

@app.route('/users')
def user_list():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('users.html', users=users)

@app.route('/items')
def item_list():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM item")
    items = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('items.html', items=items)

@app.route('/orders')
def order_list():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT o.*, i.item_name, u.user_name
        FROM orders o
        JOIN item i ON o.item_id = i.item_id
        JOIN user u ON o.buyer_id = u.user_id
    ''')
    orders = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('orders.html', orders=orders)

# ------------------- 统一商品查询页面（现在叫 query.html） -------------------
@app.route('/query', methods=['GET', 'POST'])
def query_items():
    user_list = get_all_users()
    query_type = request.values.get('query_type', '')
    selected_user = request.values.get('user_id', '')
    user_scope = request.values.get('user_scope', 'all')
    items = []
    title = ''

    db = get_db()
    cursor = db.cursor()

    # 根据选择的查询类型执行不同SQL
    if query_type == 'unsold':
        title = "未售出商品"
        cursor.execute("SELECT * FROM item WHERE status='0' OR CAST(status AS UNSIGNED)=0")

    elif query_type == 'sold':
        title = "已售商品"
        cursor.execute('''
            SELECT o.item_id, i.item_name, u.user_name, o.order_date
            FROM orders o
            JOIN item i ON o.item_id = i.item_id
            JOIN user u ON o.buyer_id = u.user_id
            ORDER BY o.order_date DESC, o.item_id
        ''')

    elif query_type == 'price_gt30':
        title = "价格大于30元"
        cursor.execute("SELECT * FROM item WHERE price>30")

    elif query_type == 'category_daily':
        title = "生活用品"
        cursor.execute("SELECT * FROM item WHERE category='DailyGoods'")

    elif query_type == 'user' and selected_user:
        title = f"用户 {selected_user} 发布的商品（{ '全部' if user_scope == 'all' else ('已售' if user_scope == 'sold' else '未售') }）"
        sql = "SELECT * FROM item WHERE seller_id=%s"
        params = [selected_user]
        if user_scope == 'sold':
            sql += " AND (status='1' OR CAST(status AS UNSIGNED)=1)"
        elif user_scope == 'unsold':
            sql += " AND (status='0' OR CAST(status AS UNSIGNED)=0)"
        sql += " ORDER BY item_id"
        cursor.execute(sql, params)
        items = cursor.fetchall()
    elif query_type:
        # 有查询类型但条件不完整（如未选择用户）
        items = []
    else:
        # 首次进入页面时不执行查询，避免 execute() first 报错
        items = []

    if query_type in ['unsold', 'sold', 'price_gt30', 'category_daily']:
        items = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('query.html',
                           users=user_list,
                           query_type=query_type,
                           selected_user=selected_user,
                           user_scope=user_scope,
                           title=title,
                           items=items)

# ------------------- 连接查询 -------------------
@app.route('/join/sold_items')
def join_sold_items():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT i.item_name, u.user_name
        FROM orders o
        JOIN item i ON o.item_id=i.item_id
        JOIN user u ON o.buyer_id=u.user_id
    ''')
    items = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('join_sold.html', items=items)

@app.route('/join/order_detail')
def join_order_detail():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT o.order_id, i.item_name, u.user_name, o.order_date
        FROM orders o
        JOIN item i ON o.item_id=i.item_id
        JOIN user u ON o.buyer_id=u.user_id
    ''')
    orders = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('order_detail.html', orders=orders)


@app.route('/join/order_detail/<item_id>')
def join_order_detail_by_item(item_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT o.order_id, i.item_name, u.user_name, o.order_date
        FROM orders o
        JOIN item i ON o.item_id=i.item_id
        JOIN user u ON o.buyer_id=u.user_id
        WHERE o.item_id=%s
    ''', (item_id,))
    orders = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('order_detail.html', orders=orders)

# 查询用户商品是否卖出（保留下拉）
@app.route('/join/user_sold', methods=['GET', 'POST'])
def join_user_sold():
    user_list = get_all_users()
    selected_user = request.form.get('user_id', '')
    items = []
    if selected_user:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT i.item_id, i.item_name, i.status,
            CASE WHEN i.status=1 THEN '已购买' ELSE '未购买' END AS is_sold
            FROM item i WHERE i.seller_id=%s
        ''', (selected_user,))
        items = cursor.fetchall()
        cursor.close()
        db.close()
    return render_template('user_sold_select.html',
                           users=user_list,
                           selected=selected_user,
                           items=items)

# ------------------- 聚合与分组 -------------------
@app.route('/agg/count')
def agg_item_count():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM item")
    res = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template('agg.html', title="商品总数", data=res)

@app.route('/agg/group')
def agg_group_category():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT category, COUNT(*) AS count FROM item GROUP BY category")
    res = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('group.html', data=res)

@app.route('/agg/avg')
def agg_avg_price():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT AVG(price) AS avg FROM item")
    res = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template('agg.html', title="商品平均价格", data=res)

@app.route('/agg/top_user')
def agg_top_user():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT seller_id, COUNT(*) AS count
        FROM item GROUP BY seller_id
        ORDER BY count DESC LIMIT 1
    ''')
    res = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template('agg.html', title="发布最多的用户", data=res)


@app.route('/stats')
def stats_dashboard():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM item")
    total = cursor.fetchone()['total']
    cursor.execute("SELECT category, COUNT(*) AS count FROM item GROUP BY category ORDER BY count DESC, category")
    by_category = cursor.fetchall()
    cursor.execute("SELECT AVG(price) AS avg_price FROM item")
    avg_price = cursor.fetchone()['avg_price']
    cursor.execute('''
        SELECT seller_id, COUNT(*) AS count
        FROM item
        GROUP BY seller_id
        ORDER BY count DESC, seller_id
        LIMIT 1
    ''')
    top_user = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template('stats.html', total=total, by_category=by_category, avg_price=avg_price, top_user=top_user)

# ------------------- 数据操作 -------------------
@app.route('/do/add_item', methods=['POST'])
def do_add_item():
    item_id = request.form.get('item_id', '').strip()
    item_name = request.form.get('item_name', '').strip()
    category = request.form.get('category', '').strip()
    seller_id = request.form.get('seller_id', '').strip()
    price_raw = request.form.get('price', '').strip()

    if not all([item_id, item_name, category, seller_id, price_raw]):
        flash("新增商品失败：请填写完整信息。", "error")
        return redirect(url_for('index'))

    db = get_db()
    cursor = db.cursor()
    try:
        price = float(price_raw)
        cursor.execute('''
            INSERT INTO item (item_id,item_name,category,price,status,seller_id)
            VALUES (%s,%s,%s,%s,0,%s)
        ''', (item_id, item_name, category, price, seller_id))
        db.commit()
        flash(f"商品 {item_id} 已新增。", "success")
    except Exception as e:
        db.rollback()
        flash(f"新增失败：{str(e)}", "error")
    cursor.close()
    db.close()
    return redirect(url_for('item_list'))

@app.route('/do/update_price', methods=['POST'])
def do_update_price():
    item_id = request.form.get('item_id', '').strip()
    price_raw = request.form.get('price', '').strip()
    if not item_id or not price_raw:
        flash("改价失败：请填写商品ID和新价格。", "error")
        return redirect(url_for('index'))

    db = get_db()
    cursor = db.cursor()
    try:
        price = float(price_raw)
        affected = cursor.execute("UPDATE item SET price=%s WHERE item_id=%s", (price, item_id))
        db.commit()
        if affected:
            flash(f"商品 {item_id} 价格已更新为 {price}。", "success")
        else:
            flash(f"未找到商品 {item_id}。", "error")
    except Exception as e:
        db.rollback()
        flash(f"改价失败：{str(e)}", "error")
    cursor.close()
    db.close()
    return redirect(url_for('item_list'))

@app.route('/do/delete_unsold', methods=['POST'])
def do_delete_unsold():
    item_id = request.form.get('item_id', '').strip()
    if not item_id:
        flash("删除失败：请填写商品ID。", "error")
        return redirect(url_for('index'))

    db = get_db()
    cursor = db.cursor()
    try:
        affected = cursor.execute("DELETE FROM item WHERE item_id=%s AND status=0", (item_id,))
        db.commit()
        if affected:
            flash(f"商品 {item_id} 已删除（未售状态）。", "success")
        else:
            flash(f"删除失败：商品不存在或已售出（{item_id}）。", "error")
    except Exception as e:
        db.rollback()
        flash(f"删除失败：{str(e)}", "error")
    cursor.close()
    db.close()
    return redirect(url_for('item_list'))

# ------------------- 购买业务 -------------------
@app.route('/buy', methods=['POST'])
def buy_item():
    item_id = request.form.get('item_id', '').strip()
    buyer_id = request.form.get('buyer_id', '').strip()
    if not item_id or not buyer_id:
        flash("购买失败：请选择商品和买家。", "error")
        return redirect(url_for('index'))

    db = get_db()
    cursor = db.cursor()
    try:
        # 行级锁：防止并发下同一商品被重复购买
        cursor.execute(
            "SELECT status, seller_id FROM item WHERE item_id=%s FOR UPDATE",
            (item_id,)
        )
        item = cursor.fetchone()

        if not item:
            flash("购买失败：商品不存在。", "error")
            return redirect(url_for('index'))
        if str(item['status']) == '1':
            flash("购买失败：商品已售出。", "error")
            return redirect(url_for('index'))
        if buyer_id == item['seller_id']:
            flash("购买失败：买家不能购买自己的商品。", "error")
            return redirect(url_for('index'))

        # 生成订单号：o + 递增数字（例如 o001、o002）
        cursor.execute("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(order_id, 2) AS UNSIGNED)), 0) AS max_no
            FROM orders
            WHERE order_id REGEXP '^o[0-9]+$'
            FOR UPDATE
        """)
        row = cursor.fetchone()
        next_no = int(row['max_no']) + 1
        new_order_id = f"o{next_no:03d}"

        # 写订单 + 改商品状态（同一事务）
        cursor.execute(
            "INSERT INTO orders (order_id, item_id, buyer_id, order_date) VALUES (%s, %s, %s, %s)",
            (new_order_id, item_id, buyer_id, datetime.now().strftime('%Y-%m-%d'))
        )
        cursor.execute("UPDATE item SET status='1' WHERE item_id=%s", (item_id,))

        db.commit()
        flash(f"购买成功：订单号 {new_order_id}。", "success")
        return redirect(url_for('order_list'))

    except Exception as e:
        db.rollback()
        flash(f"购买失败：{str(e)}", "error")
        return redirect(url_for('index'))

    finally:
        cursor.close()
        db.close()

# ------------------- 视图创建 -------------------
@app.route('/create_views')
def create_views():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        CREATE OR REPLACE VIEW sold_view AS
        SELECT i.item_name, o.buyer_id FROM orders o
        JOIN item i ON o.item_id=i.item_id
    ''')
    cursor.execute('''
        CREATE OR REPLACE VIEW unsold_view AS
        SELECT * FROM item WHERE status='0'
    ''')
    db.commit()
    cursor.close()
    db.close()
    return "已创建：已售视图、未售视图"


@app.route('/views/sold')
def view_sold_items():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM sold_view")
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('view_sold.html', data=data)


@app.route('/views/unsold')
def view_unsold_items():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM unsold_view")
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('view_unsold.html', data=data)


@app.route('/views')
def views_hub():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        CREATE OR REPLACE VIEW sold_view AS
        SELECT i.item_name, o.buyer_id FROM orders o
        JOIN item i ON o.item_id=i.item_id
    ''')
    cursor.execute('''
        CREATE OR REPLACE VIEW unsold_view AS
        SELECT * FROM item WHERE status='0'
    ''')
    cursor.execute("SELECT * FROM sold_view")
    sold_data = cursor.fetchall()
    cursor.execute("SELECT * FROM unsold_view")
    unsold_data = cursor.fetchall()
    db.commit()
    cursor.close()
    db.close()
    return render_template('views_hub.html', sold_data=sold_data, unsold_data=unsold_data)

# ------------------- 运行 -------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))