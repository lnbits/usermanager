const mapUsers = obj => {
  obj._data = _.clone(obj)
  return obj
}
const mapWallets = obj => {
  obj._data = _.clone(obj)
  return obj
}
window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  delimiters: ['${', '}'],
  data() {
    return {
      wallets: [],
      users: [],
      tab: 'inkey',
      location: location,
      hasLndhub: false,
      usersTable: {
        columns: [
          {name: 'id', align: 'left', label: 'ID', field: 'id'},
          {name: 'name', align: 'left', label: 'Username', field: 'name'},
          {name: 'extra', align: 'left', label: 'Extra', field: 'extra'}
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      walletsTable: {
        columns: [
          {name: 'id', align: 'left', label: 'ID', field: 'id'},
          {name: 'name', align: 'left', label: 'Name', field: 'name'},
          {name: 'user', align: 'left', label: 'User', field: 'user'},
          {
            name: 'adminkey',
            align: 'left',
            label: 'Admin Key',
            field: 'adminkey'
          },
          {name: 'inkey', align: 'left', label: 'Invoice Key', field: 'inkey'}
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      walletDialog: {
        show: false,
        data: {}
      },
      userDialog: {
        show: false,
        data: {}
      }
    }
  },
  computed: {
    userOptions: function () {
      return this.users.map(function (obj) {
        return {
          value: String(obj.id),
          label: String(obj.id)
        }
      })
    }
  },
  methods: {
    getUsers: function () {
      var self = this

      LNbits.api
        .request(
          'GET',
          '/usermanager/api/v1/users',
          this.g.user.wallets[0].adminkey
        )
        .then(function (response) {
          self.users = response.data
        })
    },

    openUserUpdateDialog: function (linkId) {
      var link = _.findWhere(this.users, {id: linkId})

      this.userDialog.data = _.clone(link._data)
      this.userDialog.show = true
    },
    sendUserFormData: function () {
      if (this.userDialog.data.id) {
      } else {
        var data = {
          user_name: this.userDialog.data.usrname,
          wallet_name: this.userDialog.data.walname,
          extra: {
            extra1: this.userDialog.data.extra1,
            extra2: this.userDialog.data.extra2
          }
        }
      }
      {
        this.createUser(data)
      }
    },

    createUser: function (data) {
      var self = this
      LNbits.api
        .request(
          'POST',
          '/usermanager/api/v1/users',
          this.g.user.wallets[0].adminkey,
          data
        )
        .then(function (response) {
          self.userDialog.show = false
          self.userDialog.data = {}
        })
        .finally(function () {
          self.getWallets()
          self.getUsers()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    deleteUser: function (userId) {
      var self = this
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this User link?')
        .onOk(function () {
          LNbits.api
            .request(
              'DELETE',
              '/usermanager/api/v1/users/' + userId,
              self.g.user.wallets[0].adminkey
            )
            .then(function (response) {
              this.users = _.reject(this.users, obj => obj.id === userId)
              this.wallets = _.reject(this.wallets, obj => obj.user === userId)
            })
            .finally(function () {
              self.getWallets()
              self.getUsers()
            })
            .catch(function (error) {
              LNbits.utils.notifyApiError(error)
            })
        })
    },

    exportUsersCSV: function () {
      LNbits.utils.exportCSV(this.usersTable.columns, this.users)
    },
    getWallets: function () {
      self = this
      LNbits.api
        .request(
          'GET',
          '/usermanager/api/v1/wallets',
          this.g.user.wallets[0].adminkey
        )
        .then(function (response) {
          self.wallets = response.data
        })
    },
    openWalletUpdateDialog: function (linkId) {
      var link = _.findWhere(this.users, {id: linkId})

      this.walletDialog.data = _.clone(link._data)
      this.walletDialog.show = true
    },
    sendWalletFormData: function () {
      if (this.walletDialog.data.id) {
      } else {
        var data = {
          user_id: this.walletDialog.data.user,
          wallet_name: this.walletDialog.data.walname
        }
      }
      {
        this.createWallet(data)
      }
    },
    createWallet: function (data) {
      var self = this
      LNbits.api
        .request(
          'POST',
          '/usermanager/api/v1/wallets',
          this.g.user.wallets[0].adminkey,
          data
        )
        .then(function (response) {
          self.walletDialog.show = false
          self.walletDialog.data = {}
        })
        .finally(function () {
          self.getWallets()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    deleteWallet: function (userId) {
      var self = this
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this wallet link?')
        .onOk(function () {
          LNbits.api
            .request(
              'DELETE',
              '/usermanager/api/v1/wallets/' + userId,
              self.g.user.wallets[0].adminkey
            )
            .then(function (response) {
              self.wallets = _.reject(self.wallets, function (obj) {
                return obj.id == userId
              })
            })
            .catch(function (error) {
              LNbits.utils.notifyApiError(error)
            })
        })
    },
    exportWalletsCSV: function () {
      LNbits.utils.exportCSV(this.walletsTable.columns, this.wallets)
    }
  },
  created: function () {
    this.getUsers()
    this.getWallets()
    if (this.g.user.extensions.includes('lndhub')) {
      this.hasLndhub = true
    }
  }
})
