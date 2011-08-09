# This file is part of the Fluid Nexus Website.
# 
# the Fluid Nexus Website is free software: you can redistribute it and/or 
# modify it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
# 
# the Fluid Nexus Website is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with the Fluid Nexus Website.  If not, see 
# <http://www.gnu.org/licenses/>.


# from http://pythonguy.wordpress.com/2007/07/27/sqlalchemy-rocks/

class Subset(object):

    def __init__(self, query, first, num):
        self.query = query

        self.first = int(first)
        assert (self.first >= 0), "First must be positive"

        self.num = int(num)
        assert (self.num > 0), "Num must be greater than 0"

        self.total = self.query.count()
        self.results = tuple(self.query.limit(self.num).offset(self.first).all())

        self.last = self.first + len(self.results) - 1

    def __len__(self):
        return len(self.results)

    def __getitem__(self, i):
        return self.results[i]

    def __iter__(self):
        return iter(self.results)

class Pager(Subset):

    def __init__(self, query, page, results_per_page):
        self.page = int(page)
        assert (self.page > 0), "Page must be greater than 0"

        self.results_per_page = results_per_page
        Subset.__init__(self, query = query, first = (page - 1) * results_per_page, num = results_per_page)

        self.pages = (self.total - 1)/self.results_per_page + 1
